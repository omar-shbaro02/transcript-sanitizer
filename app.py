import argparse
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from anonymizer.processor import DEFAULT_CONFIG_PATH, process_transcript


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "TranscriptSanitizer" / "output"


class TranscriptSanitizerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Transcript Sanitizer")
        self.geometry("720x360")
        self.minsize(620, 320)

        self.selected_file = tk.StringVar(value="")
        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.status = tk.StringVar(value="Select a TXT or DOCX transcript to begin.")
        self.anonymize_orgs = tk.BooleanVar(value=True)
        self.anonymize_locations = tk.BooleanVar(value=True)
        self.anonymize_dates = tk.BooleanVar(value=False)
        self.save_mapping = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self, padx=18, pady=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)

        tk.Button(container, text="Select transcript", command=self.select_file, width=20).grid(row=0, column=0, sticky="w")
        tk.Label(container, textvariable=self.selected_file, anchor="w", relief="sunken", padx=8).grid(row=0, column=1, sticky="ew", padx=(10, 0))

        options = tk.LabelFrame(container, text="Options", padx=12, pady=10)
        options.grid(row=1, column=0, columnspan=2, sticky="ew", pady=16)
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)

        tk.Checkbutton(options, text="Anonymize organizations", variable=self.anonymize_orgs).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(options, text="Anonymize locations", variable=self.anonymize_locations).grid(row=0, column=1, sticky="w")
        tk.Checkbutton(options, text="Anonymize dates", variable=self.anonymize_dates).grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Checkbutton(options, text="Save local mapping file", variable=self.save_mapping).grid(row=1, column=1, sticky="w", pady=(8, 0))

        tk.Button(container, text="Output folder", command=self.select_output, width=20).grid(row=2, column=0, sticky="w")
        tk.Label(container, textvariable=self.output_dir, anchor="w", relief="sunken", padx=8).grid(row=2, column=1, sticky="ew", padx=(10, 0))

        actions = tk.Frame(container)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=18)
        tk.Button(actions, text="Process", command=self.process_file, width=20).pack(side="left")
        tk.Button(actions, text="Open output folder", command=self.open_output_folder, width=20).pack(side="left", padx=(10, 0))

        tk.Label(container, textvariable=self.status, anchor="w", justify="left", wraplength=660).grid(row=4, column=0, columnspan=2, sticky="ew")

    def select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select transcript",
            filetypes=[("Transcript files", "*.txt *.docx"), ("Text files", "*.txt"), ("Word documents", "*.docx")],
        )
        if path:
            self.selected_file.set(path)
            self.status.set("Ready to process.")

    def select_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder", initialdir=self.output_dir.get())
        if path:
            self.output_dir.set(path)

    def process_file(self) -> None:
        if not self.selected_file.get():
            messagebox.showwarning("Transcript Sanitizer", "Select a transcript file first.")
            return

        self.status.set("Processing locally...")
        self.update_idletasks()
        try:
            result = process_transcript(
                self.selected_file.get(),
                self.output_dir.get(),
                DEFAULT_CONFIG_PATH,
                {
                    "anonymize_organizations": self.anonymize_orgs.get(),
                    "anonymize_locations": self.anonymize_locations.get(),
                    "anonymize_dates": self.anonymize_dates.get(),
                    "save_local_mapping": self.save_mapping.get(),
                },
            )
        except Exception as exc:
            self.status.set("Processing failed.")
            messagebox.showerror("Transcript Sanitizer", f"Processing failed:\n{exc}")
            return

        self.status.set(f"Done. Anonymized {result['entity_count']} detected entity occurrence(s).")
        messagebox.showinfo(
            "Transcript Sanitizer",
            "Processing complete.\n\n"
            f"Anonymized transcript:\n{result['anonymized_txt']}\n\n"
            f"Report:\n{result['report']}",
        )

    def open_output_folder(self) -> None:
        Path(self.output_dir.get()).mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(self.output_dir.get())
            elif sys.platform == "darwin":
                import subprocess

                subprocess.run(["open", self.output_dir.get()], check=False)
            else:
                import subprocess

                subprocess.run(["xdg-open", self.output_dir.get()], check=False)
        except Exception as exc:
            messagebox.showerror("Transcript Sanitizer", f"Could not open output folder:\n{exc}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local-only transcript anonymizer.")
    parser.add_argument("--input", help="Path to .txt or .docx transcript")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Config JSON path")
    parser.add_argument("--anonymize-dates", action="store_true", help="Override config to anonymize dates")
    parser.add_argument("--no-map", action="store_true", help="Do not save a local mapping file")
    return parser.parse_args(argv)


def run_cli(args: argparse.Namespace) -> int:
    overrides = {}
    if args.anonymize_dates:
        overrides["anonymize_dates"] = True
    if args.no_map:
        overrides["save_local_mapping"] = False

    result = process_transcript(args.input, args.output, args.config, overrides)
    print("Processing complete.")
    print(f"Anonymized transcript: {result['anonymized_txt']}")
    print(f"Processing report: {result['report']}")
    if result.get("mapping_file"):
        print(f"Local mapping file: {result['mapping_file']}")
        print("Warning: do not upload mapping files to external AI tools.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.input:
        return run_cli(args)

    app = TranscriptSanitizerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
