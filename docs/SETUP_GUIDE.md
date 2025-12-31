# 🌑 MaxOS Quick-Start Guide (Beginner Friendly)

Welcome to MaxOS! This guide will help you get your AI Operating System up and running in minutes, even if you've never used a terminal before.

---

## 1. Get Your "Brain" (Google API Key)

MaxOS uses Google's Gemini AI to think and listen. You need an API key to wake him up.

1.  Go to the [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Sign in with your Google account.
3.  Click the blue button that says **"Create API key"**.
4.  Copy the long string of letters and numbers. **Don't share this with anyone!**

---

## 2. Set Up Your Configuration

Now we need to tell MaxOS who you are and give him his brain.

1.  Find the file in this folder named `.env.example`.
2.  **Rename it to just `.env`** (Remove the `.example` part).
3.  Open that `.env` file with a text editor (Notepad, TextEdit, or VS Code).
4.  Find the line that says: `GOOGLE_API_KEY=your_key_here`
5.  Replace `your_key_here` with the API key you copied from Google.
6.  Save the file.

---

## 3. Choose Your Launch Mode

### Option A: The "Easy Mode" (Docker) 🐳
*Best if you just want to play with MaxOS inside your current computer.*

1.  Make sure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
2.  Open your terminal in this folder.
3.  Type this and press Enter:
    ```bash
    docker-compose up --build
    ```
4.  Wait for the code to finish ("MaxOS V3 // Connected" will appear).
5.  Open your browser and type: `http://localhost:5173`
6.  **Enjoy!**

### Option B: The "Pro Mode" (Native) ⚙️
*Best if you want Max to have real control over your PC.*

1.  Open your terminal in this folder.
2.  Run the setup:
    ```bash
    ./scripts/bootstrap.sh
    source .venv/bin/activate
    ```
3.  Start Max:
    ```bash
    python max_os/runner.py
    ```
4.  Max will start listening! Say **"Max, search for my downloads"** or type in the GUI.

---

## 🛡️ Pro Tips for Beginners

*   **Wake Word**: Say "Max" to get his attention before any command.
*   **Safety First**: Max will ask for permission before deleting or moving large files.
*   **Kiosk Mode**: Click the lock icon in the GUI to make Max take over your whole screen!

---

## 🆘 Troubleshooting

*   **"Key not found"**: Double check your `.env` file. Make sure there are no spaces around the `=`.
*   **"Docker not running"**: Open the Docker Desktop app first.
*   **Silence**: If Max isn't talking, check your speaker volume and ensure your `GOOGLE_API_KEY` is active.

**You're all set! Welcome to the future of computing.** 🌑🚀
