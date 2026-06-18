use tauri::{
    Manager,
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, TrayIconBuilder, TrayIconEvent},
};
use std::net::TcpStream;
use std::process::{Command, Child};
use std::sync::Mutex;
#[cfg(windows)]
use std::os::windows::process::CommandExt;

const CREATE_NO_WINDOW: u32 = 0x08000000;

const BACKEND_EXE: &str = "onestopservice-backend.exe";
const BACKEND_PORT: u16 = 8710;

struct BackendProc(Mutex<Option<Child>>);

/// Drop 安全网：无论什么原因退出，都杀掉后端子进程
/// （Rust 的 Child::drop() 在 Windows 上不会自动杀进程，必须显式 kill）
impl Drop for BackendProc {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.take() {
                eprintln!("[OneStopService] Cleaning up backend (PID {})", child.id());
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

/// 检查后端端口是否已被占用（dev 模式下 Python 直接跑的）
fn is_port_open(port: u16) -> bool {
    TcpStream::connect(("127.0.0.1", port)).is_ok()
}

/// 尝试查找 backend exe，找不到时尝试用 pythonw 直接跑源码
fn spawn_backend(app: &tauri::App) -> Result<(), String> {
    // 优先找打包的 exe
    let exe_candidates = [
        app.path().resource_dir().ok()
            .map(|d| d.join("resources").join(BACKEND_EXE)),
        std::env::current_dir().ok()
            .map(|d| d.join("src-tauri").join("resources").join(BACKEND_EXE)),
        std::env::current_dir().ok()
            .map(|d| d.join(BACKEND_EXE)),
    ];

    // 试试 exe
    for candidate in exe_candidates.iter().flatten() {
        if candidate.exists() {
            eprintln!("[OneStopService] Starting backend exe: {:?}", candidate);
            let mut cmd = Command::new(candidate);
            #[cfg(windows)]
            cmd.creation_flags(CREATE_NO_WINDOW);
            return match cmd.spawn() {
                Ok(child) => {
                    let pid = child.id();
                    app.manage(BackendProc(Mutex::new(Some(child))));
                    eprintln!("[OneStopService] Backend exe started (PID {})", pid);
                    Ok(())
                }
                Err(e) => Err(format!("Failed to start exe: {}", e)),
            };
        }
    }

    // exe 不存在，尝试 pythonw backend/main.py（省去 PyInstaller 编译步骤）
    eprintln!("[OneStopService] Backend exe not found, trying pythonw...");
    let mut cmd = Command::new("pythonw");
    cmd.arg("backend/main.py");
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);
    match cmd.spawn() {
        Ok(child) => {
            let pid = child.id();
            app.manage(BackendProc(Mutex::new(Some(child))));
            eprintln!("[OneStopService] Backend started via pythonw (PID {})", pid);
            Ok(())
        }
        Err(e) => {
            let msg = format!("Cannot start backend: exe not found and pythonw failed: {}", e);
            eprintln!("[OneStopService] {}", msg);
            Err(msg)
        }
    }
}

/// 杀掉后端子进程
fn kill_backend(app: &tauri::AppHandle) {
    let mut killed = false;
    // 1) 优雅：通过托管的子进程句柄杀
    if let Some(state) = app.try_state::<BackendProc>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(mut child) = guard.take() {
                let pid = child.id();
                eprintln!("[OneStopService] Stopping backend (PID {})", pid);
                if child.kill().is_ok() {
                    let _ = child.wait();
                    killed = true;
                    eprintln!("[OneStopService] Backend (PID {}) stopped", pid);
                }
            }
        }
    }
    // 2) 暴力扫尾：用 taskkill 杀所有 backend exe（不管是谁启动的）
    if !killed {
        eprintln!("[OneStopService] Force-killing backend process...");
        #[cfg(windows)]
        {
            use std::process::Command as StdCommand;
            // 杀打包的 exe
            let _ = StdCommand::new("taskkill")
                .args(["/F", "/IM", "onestopservice-backend.exe"])
                .creation_flags(CREATE_NO_WINDOW)
                .status();
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // 端口已被占用（dev:all 模式），无需启动
            if is_port_open(BACKEND_PORT) {
                eprintln!("[OneStopService] Backend already running on port {}", BACKEND_PORT);
            } else {
                let _ = spawn_backend(app);
            }

            // ── 系统托盘 ──
            let show_item = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
            let hide_item = MenuItem::with_id(app, "hide", "隐藏到托盘", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &hide_item, &quit_item])?;

            let img = image::load_from_memory(include_bytes!("../icons/32x32.png"))
                .expect("加载托盘图标失败")
                .to_rgba8();
            let (width, height) = img.dimensions();
            let icon = Image::new_owned(img.into_raw(), width, height);

            TrayIconBuilder::new()
                .icon(icon)
                .menu(&menu)
                .tooltip("OneStopService - 本地服务一条龙管理")
                .on_menu_event(|app, event| {
                    match event.id().as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "hide" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.hide();
                            }
                        }
                        "quit" => {
                            kill_backend(app);
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    // 左键单击：切换窗口显示/隐藏
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            // 点击关闭按钮 → 隐藏到托盘，不退出
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                eprintln!("[OneStopService] Minimizing to tray");
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // 应用退出时确保后端进程被杀死
            if let tauri::RunEvent::Exit = event {
                kill_backend(app_handle);
            }
        });
}
