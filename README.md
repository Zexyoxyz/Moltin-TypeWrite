# Moltin TypeWriter

**Moltin TypeWriter** is a modern, vibe-coded, privacy-first Markdown editor and personal knowledge management (PKM) application built exclusively for Windows.

Designed for writers, developers, researchers, and students, Moltin TypeWriter combines the simplicity of local Markdown files with powerful knowledge management features and an optional AI writing assistant—all without locking your notes behind a cloud subscription.

Unlike many note-taking platforms, **your data always belongs to you**. Every note is stored as a standard `.md` file on your own computer, making your knowledge portable, future-proof, and compatible with countless other Markdown applications.

---

## ✨ Features

### 📝 Powerful Markdown Editor

* Clean, distraction-free writing experience
* Markdown syntax highlighting
* Live preview
* Fast, responsive editing
* Auto-save
* Multiple tabs for working on several notes simultaneously

### 🧠 Personal Knowledge Management

* Organize notes into local vaults
* Wiki-style `[[Internal Links]]`
* Backlinks
* Tag management
* Full-text search
* Interactive knowledge graph to visualize relationships between notes

### 🤖 AI Writing Assistant *(Optional)*

Bring your own API key and choose the AI provider that works best for you.

Supported providers include:

* OpenAI
* Anthropic
* Google Gemini
* Groq
* Local Ollama models

Use AI to:

* Correct grammar and spelling
* Improve clarity and readability
* Rewrite sentences
* Change writing tone
* Summarize documents
* Expand ideas into full paragraphs
* Brainstorm content
* Continue unfinished writing

Your API keys are encrypted locally using **AES-256-GCM** and are never shared unless you explicitly use an AI provider.

### 🔒 Privacy First

* No accounts required
* No cloud lock-in
* No telemetry
* No subscriptions
* No vendor-controlled storage

Your vaults remain on your computer as ordinary folders containing standard Markdown files. If you want cloud syncing, simply use Dropbox, OneDrive, Google Drive, Git, Syncthing, or any file synchronization tool of your choice.

### ⚡ Native Windows Experience

Built with **PyQt6**, Moltin TypeWriter delivers the speed and responsiveness of a native desktop application while remaining lightweight and easy to install.

---

# Why Moltin TypeWriter?

Most modern note-taking apps expect you to trust them with your knowledge.

Moltin TypeWriter takes a different approach.

Your notes stay on your computer.

Your files remain plain Markdown.

Your AI provider is your choice.

Your workflow isn't tied to a subscription or proprietary ecosystem.

Whether you're writing documentation, building a personal wiki, drafting novels, managing research, or simply taking notes, Moltin TypeWriter provides a fast, modern workspace that puts you in complete control.

---

# Getting Started

## Requirements

* Windows 10 or Windows 11
* Python 3.11 or newer
* Python added to your system `PATH`

---

## Running from Source

1. Clone this repository.
2. Open the project folder.
3. Double-click **`run.bat`**.

The launcher will automatically:

* Create a Python virtual environment
* Install all required dependencies
* Launch Moltin TypeWriter

No manual setup is required.

---

# Building a Windows Installer

To package Moltin TypeWriter as a standalone Windows installer:

### Requirements

* Inno Setup 6
* PyInstaller

### Build Steps

1. Install Inno Setup 6.
2. Open the project folder.
3. Double-click **`build.bat`**.

The build script will:

* Compile the application using PyInstaller
* Bundle all required assets
* Generate a professional Windows installer
* Output the installer to the `dist/` directory

---

# Project Goals

Moltin TypeWriter aims to be:

* 🚀 Fast and lightweight
* 🔒 Privacy-first
* 📝 Markdown-native
* 🧠 AI-enhanced (without being AI-dependent)
* 📁 Local-first
* 🔌 Extensible
* 💙 Open source

---

## License

This project is licensed under the MIT License.
