# Stellar Career Agent

Enterprise-grade autonomous job application agent and career assistant. Powered by FastAPl, Playwright, React, and TanStack Router.

---

## 🚀 Development Browser Mode

The Auto Apply engine features a dedicated **Development Browser Mode** to streamline testing, session management, and debugging.

### Features
1. **Persistent Context & Cookie Reuse**: Unlike Production Mode (which runs an isolated temporary browser session), Development Mode launches Chrome with a persistent user profile. This allows you to log into job portals (e.g. LinkedIn, Indeed, Glassdoor) once and reuse those cookies/sessions for all subsequent automated applications.
2. **Inspect Mode (Keep Open)**: The browser window is kept open after the job application is completed. It will remain open for inspection until you manually close the browser window or click **"End Debug Session"** in the UI.
3. **Active Lock Detection**: To prevent Chrome profile corruption, the system detects if the selected profile is already open in another Google Chrome instance. If a lock is detected, the run terminates safely and warns the user to close Chrome or select an alternative profile path.
4. **Interactive UI Configuration**: Set the mode, Chrome profile directory, custom browser executable paths, slow-mo pacing, and debugging verbosity directly from the **Settings > Browser Automation** page.

---

### Setup Instructions

#### 1. Configure the Browser Automation settings in the UI
1. Start the application frontend and backend.
2. Navigate to the **Settings** page from the sidebar.
3. Select the **Browser Automation** tab.
4. Switch the **Browser Automation Mode** to **Development Mode**.
5. Specify your custom **Chrome Profile Data Directory** (or use the safe default `StellarAutomation` directory auto-generated under your local Chrome user data path).
6. Click **Save Browser Settings**.

#### 2. Log in to Job Portals (Optional, for session sharing)
To run automation using your active login sessions:
1. Open Google Chrome manually using the profile folder you configured (e.g., launch chrome via CLI with `--user-data-dir="<path_to_configured_profile>"`).
2. Log in to job boards such as `LinkedIn.com`, `Indeed.com`, or `Naukri.com`.
3. Close all Chrome windows running under that profile path so the lock is released.
4. Run the Stellar Career Agent Auto-Apply tool. Playwright will automatically inherit the authenticated sessions!

#### 3. Safety Guidelines
* **Do not use your main Chrome profile** while the automation runs. Set up a dedicated automation profile folder (e.g. `C:\Users\<Name>\AppData\Local\Google\Chrome\User Data\StellarAutomation`).
* If you see the error:
  `Profile is locked or in use by another Chrome process.`
  Make sure all Chrome windows using that user-data directory are completely closed before starting the run.

---

## 🛠️ Tech Stack & Commands

### Backend (FastAPI)
* **Directory**: `stellar-backend`
* **Run Server**:
  ```bash
  cd stellar-backend
  venv\Scripts\activate
  python main.py
  ```
* **Run Test Suite**:
  ```bash
  python -m pytest test_queue_lifecycle.py test_browser_config.py -v
  ```

### Frontend (React + TanStack Router)
* **Run Developer Server**:
  ```bash
  npm run dev
  ```
