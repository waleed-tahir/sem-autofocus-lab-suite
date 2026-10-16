using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

namespace AutofocusLabSuite
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string pythonExe = @"C:\Users\PC\AppData\Local\Programs\Python\Python312\python.exe";

            if (!File.Exists(pythonExe))
            {
                // Fallback to checking PATH or .venv
                string venvPy = Path.Combine(baseDir, @".venv\Scripts\python.exe");
                if (File.Exists(venvPy))
                {
                    pythonExe = venvPy;
                }
                else
                {
                    pythonExe = "python.exe";
                }
            }

            // Check if server is already responding
            bool serverReady = IsServerResponding("http://127.0.0.1:8000/api/status");
            Process backendProcess = null;

            if (!serverReady)
            {
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = pythonExe,
                    Arguments = "-m uvicorn autofocus_suite.server.app:app --host 127.0.0.1 --port 8000",
                    WorkingDirectory = baseDir,
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    WindowStyle = ProcessWindowStyle.Hidden
                };

                try
                {
                    backendProcess = Process.Start(psi);
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Failed to launch Python backend: " + ex.Message, "Autofocus Lab Suite Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                // Poll for server startup (up to 15 seconds)
                int retries = 0;
                while (retries < 30 && !IsServerResponding("http://127.0.0.1:8000/api/status"))
                {
                    Thread.Sleep(500);
                    retries++;
                }
            }

            // Launch Desktop App Window using Chrome/Edge App Mode or Default Browser
            string targetUrl = "http://127.0.0.1:8000";
            Process appWindow = null;

            string[] candidateBrowsers = new string[]
            {
                @"C:\Program Files\Google\Chrome\Application\chrome.exe",
                @"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Google\Chrome\Application\chrome.exe"),
                @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                @"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            };

            string browserPath = null;
            foreach (string p in candidateBrowsers)
            {
                if (File.Exists(p))
                {
                    browserPath = p;
                    break;
                }
            }

            if (!string.IsNullOrEmpty(browserPath))
            {
                ProcessStartInfo bPsi = new ProcessStartInfo
                {
                    FileName = browserPath,
                    Arguments = string.Format("--app={0} --window-size=1440,940", targetUrl),
                    UseShellExecute = false
                };
                appWindow = Process.Start(bPsi);
            }
            else
            {
                Process.Start(new ProcessStartInfo(targetUrl) { UseShellExecute = true });
            }

            // If we launched the app window and spawned a backend, monitor window closure
            if (appWindow != null && backendProcess != null)
            {
                appWindow.WaitForExit();
                try
                {
                    if (!backendProcess.HasExited)
                    {
                        backendProcess.Kill();
                    }
                }
                catch { }
            }
        }

        static bool IsServerResponding(string url)
        {
            try
            {
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
                req.Timeout = 800;
                req.Method = "GET";
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                {
                    return resp.StatusCode == HttpStatusCode.OK;
                }
            }
            catch
            {
                return false;
            }
        }
    }
}
