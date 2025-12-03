# BeatRooter - Cyber Investigation & Threat Mapping Tool
To plant beets, you have to start with the root.

<p align="center">
  <img src="/Assets/BeatRooter_logo.png" alt="logo"/>
</p>


## 📋 Overview

**BeatRooter** is a powerful digital forensics and cyber investigation tool designed to help security analysts map, visualize, and analyze complex threat landscapes. Built with PyQt6, it provides an intuitive graph-based interface for connecting digital evidence and building comprehensive investigation timelines.

## 🚀 Features

### 🔍 Investigation Capabilities
- **Interactive Graph Canvas** - Drag-and-drop interface for building investigation maps
- **Multiple Node Types** - IP addresses, domains, users, credentials, attacks, vulnerabilities, hosts, notes, screenshots, commands, and scripts
- **Relationship Mapping** - Visual connections between investigation elements
- **Real-time Collaboration** - Share and collaborate on investigation boards

### 🎨 Visualization
- **Cyber Security Themes** - Multiple visual themes (Cyber Modern, Hacker Dark, Detective Classic)
- **Pixel Art Style** - Retro terminal-inspired design
- **Dynamic Connections** - Smart edge routing with hover effects
- **Grid System** - Organized canvas with snap-to-grid functionality

### 💾 Data Management
- **Native File Format** (.brt) - Custom BeatRooter Tree format
- **Export Options** - PNG, SVG, JSON export capabilities
- **Image Metadata Extraction** - Automatic EXIF and PNG metadata parsing
- **Base64 Image Support** - Embedded image data storage

### 🔧 Technical Features
- **Zoom & Pan** - Smooth canvas navigation with Alt+drag
- **Connection Mode** - Visual relationship creation between nodes
- **Search & Filter** - Quick node discovery and filtering
- **Detail Panel** - Comprehensive node editing and metadata viewing

## 🛠 Installation

### Prerequisites
- Python 3.8+
- PyQt6
- Pillow (PIL)
- Other dependencies (see requirements.txt)

### Quick Start
```bash
# Clone the repository
git clone https://github.com/Samucahub/BeatRooter.git
cd BeatRooter
cd BeatRooter_Code

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Dependencies
```text
PyQt6>=6.4.0
Pillow>=9.0.0
```

## Project Structure

```
beatrooter/
├── core/                 # Core application logic
│   ├── graph_manager.py  # Graph data management
│   ├── node_factory.py   # Node creation and templates
│   ├── storage_manager.py # File I/O operations
│   └── theme_manager.py  # UI theme management
├── models/               # Data models
│   ├── node.py          # Node data structure
│   └── edge.py          # Edge/connection model
├── ui/                   # User interface components
│   ├── main_window.py   # Main application window
│   ├── canvas_widget.py # Graph canvas implementation
│   ├── node_widget.py   # Node visual representation
│   ├── toolbox.py       # Node creation toolbox
│   ├── detail_panel.py  # Node detail editor
│   └── dynamic_edge.py  # Connection visualization
├── utils/               # Utility functions
│   ├── image_utils.py   # Image processing and metadata
│   └── script_editor.py # Code editor for scripts
└── assets/              # Application resources
    └── themes/          # UI theme definitions
```

## Usage Guide

### Creating Investigations
1. **Start New Investigation**: File → New Investigation
2. **Add Nodes**: Use toolbox or right-click canvas
3. **Create Connections**: Right-click node → "CONNECT" or use connection mode
4. **Add Evidence**: Import screenshots with automatic metadata extraction

### Working with Nodes
- **Double-click** any node to edit details
- **Right-click** for context menu (connect, edit, delete)
- **Drag** to reposition nodes
- **Alt + Drag** to pan the canvas

### Advanced Features
- **Script Nodes**: Built-in code editor with syntax highlighting
- **Screenshot Nodes**: Automatic metadata extraction (EXIF, PNG info)
- **Credential Nodes**: Password/hash type switching
- **Search & Filter**: Quick navigation in complex investigations

---

## 🎨 Themes

### Cyber Modern (Default)
- Dark blue color scheme
- Clean, professional appearance
- Optimized for long investigation sessions

### Hacker Dark
- Classic green-on-black terminal style
- Retro hacker aesthetic
- High contrast for focused analysis

### Detective Classic
- Warm, classic investigation board feel
- Parchment-inspired colors
- Traditional detective workflow

---

## Node Types

| Type | Description | Key Fields |
|------|-------------|------------|
| **IP** | IP addresses and network entities | Address, Geo-location, Threat Level |
| **Domain** | Domain names and DNS records | Name, Registrar, Creation Date |
| **User** | User accounts and identities | Username, Email, Role, Department |
| **Credential** | Passwords and authentication data | Username, Password/Hash, Type |
| **Attack** | Attack techniques and patterns | Type, Technique, Success Status |
| **Vulnerability** | Security vulnerabilities | CVE, Severity, Exploitation Status |
| **Host** | Computer systems and devices | Hostname, IP, OS, Services |
| **Note** | Investigation notes and findings | Title, Content, Timestamp |
| **Screenshot** | Visual evidence with metadata | Filename, Dimensions, EXIF Data |
| **Command** | System commands and execution | Command, Exit Code, Output |
| **Script** | Code snippets and scripts | Filename, Language, Content |

---

## License

BeatRooter is released under the your MOM License.

---

## 🫦 Kiss for devs

  <a href="https://github.com/Samucahub/BeatRooter/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=Samucahub/BeatRooter" />
  </a>
