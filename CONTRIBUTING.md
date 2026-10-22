# Contributing to PC Remote 🤝

First off, thank you for considering contributing to **PC Remote**! It is community contributions and open-source collaboration that make projects like this great.

---

## 🧭 Code of Conduct

Please be respectful, constructive, and considerate when interacting with contributors and maintainers across issues, discussions, and pull requests.

---

## 🛠️ How to Contribute

### 1. Reporting Bugs
- Search existing [Issues](https://github.com/mohammed-alattas/pc-remote/issues) to see if the problem has already been reported.
- If not, open a new issue using the **Bug Report** template.
- Include your Windows version (e.g. Windows 11 23H2), Python version, mobile browser details, and terminal logs.

### 2. Suggesting Features & Integrations
- Open a new issue using the **Feature Request** template.
- Describe the hardware or software you want to integrate (e.g. Philips Hue, Voicemeeter, Home Assistant, Corsair iCUE).
- Mention any known Windows APIs, libraries, or protocols that could be used.

### 3. Submitting Pull Requests (PRs)
1. Fork the repository and clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pc-remote.git
   cd pc-remote
   ```
2. Create a new topic branch:
   ```bash
   git checkout -b feature/my-cool-feature
   ```
3. Set up your local development environment:
   ```bash
   .\setup.bat
   ```
4. Make your changes adhering to the coding standards below.
5. Test your changes thoroughly on both Windows and mobile viewports.
6. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat(obs): add replay buffer status indicator"
   ```
7. Push to your fork and submit a Pull Request to `main`.

---

## 📜 Coding Guidelines

### Python (Backend)
- Follow **PEP 8** style guidelines.
- Use explicit type hints (`typing.Optional`, `typing.List`, `typing.Dict`).
- **COM Safety:** Never invoke Windows CoreAudio (`pycaw`) directly from async FastAPI route handlers. Always route through `server.services.audio_svc._run_in_audio_thread` to maintain Single-Threaded Apartment (STA) integrity.
- Keep subprocess executions non-blocking and specify `creationflags=0x08000000` (`CREATE_NO_WINDOW`) when launching background Windows utilities so command windows do not pop up on the desktop.

### JavaScript & CSS (Frontend)
- **Zero-Build Philosophy:** Do NOT introduce bundlers (Webpack, Vite, Rollup) or heavy frontend frameworks (React, Vue). The app intentionally serves vanilla ES6 modules directly to keep development and deployment zero-friction.
- Use `import` / `export` ES6 syntax.
- **Design Tokens:** Always reference colors, radii, shadows, and spacing from `web/css/tokens.css` (e.g., `var(--bg-card)`, `var(--accent)`, `var(--r-sm)`). Never hardcode ad-hoc hex colors in component CSS.
- **Responsive Testing:** Verify your UI in both **Mobile Portrait** (one-handed phone use) and **Landscape Cockpit** (desk-docked horizontal display).

---

## 🧪 Verification & Diagnostics

Before opening a PR:
- Verify that the FastAPI server boots cleanly with `run.bat`.
- If modifying audio logic, run:
  ```powershell
  python -m tests.diagnostics.test_audio
  ```
- Check that the PIN security screen still blocks unauthorized requests.

---

Thank you for helping make PC Remote even better! 🚀
