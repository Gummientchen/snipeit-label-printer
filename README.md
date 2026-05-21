# Snipe-IT Asset Label Printer

A lightweight Python application that queries the Snipe-IT API for asset details (by serial number or asset page URL), generates a PDF label containing a QR code and asset information, and automatically prints it to a Zebra label printer.

## Features
- **Fast Startup**: Managed using `uv` for python environments and package dependencies.
- **Easy Configuration**: Simple `.env` configuration file instead of python settings.
- **Windows Integration**: Automatic local printer validation showing available printers on mismatch.
- **Dynamic Formatting**: Custom field display (e.g., Klasse) and automatic layout offsets.
- **Smart Labels**: Automatically prints custom owner details instead of default asset name if the "Owner" custom field is filled.

---

## Quick Start (Windows)

The project includes an automatic launcher script `run_app.bat` that handles installation, setup, and launching:

1. Double-click `run_app.bat`.
2. If **`uv`** is not installed, it will automatically download and install it.
3. If no `.env` file exists, it will create one from `.env.sample` and ask you to fill in your API credentials.
4. It will prepare the Python environment, download dependencies, and run the script automatically.

---

## Manual Setup and Installation

### 1. Install `uv`
`uv` is an extremely fast Python package and project manager. Install it using the following commands:

*   **Windows**:
    ```powershell
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
*   **macOS / Linux**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

### 2. Prepare Environment
Navigate to the project directory and synchronize the virtual environment:
```bash
uv sync
```
This automatically sets up a `.venv` directory and installs all dependencies specified in the project file.

### 3. Configure Settings
Copy `.env.sample` to a new file named `.env`:
```bash
copy .env.sample .env
```
Open `.env` and fill in the required fields:
- **`SNIPEIT_URL`**: The base URL of your Snipe-IT instance (e.g., `https://assets.example.com`).
- **`SNIPEIT_API_KEY`**: Your Snipe-IT API Bearer Token.
- **`PRINTER_NAME`**: The exact name of your Zebra label printer as it appears in Windows.
- **`GHOSTSCRIPT_PATH`**: Path to the Ghostscript executable (e.g., `C:\Program Files\gs\gs10.05.1\bin\gswin64c.exe`), which is required on Windows for direct printing.

### 4. Run the Script
To run the label printer utility:
```bash
uv run python asset_label_app.py
```

---

## Troubleshooting

- **Configuration Errors**: If required environment variables are missing or have incorrect formats (like non-numeric dimensions), the application will print structured validation errors at startup and exit safely.
- **Ghostscript Validation**: Direct printing on Windows requires Ghostscript. The loader checks if the Ghostscript path exists on disk and alerts you if it is missing or misconfigured.
- **Printer Not Found**: If the configured printer cannot be reached, the application prints a list of all active Windows system printers so you can copy the correct name into your `.env`.
