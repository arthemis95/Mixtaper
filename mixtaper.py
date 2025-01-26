import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pygame import mixer
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.flac import FLAC
import threading
import shutil

class MixtapeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cassette Mixtape Tool")

        # Initialize variables
        self.mixtape = {"A": [], "B": []}  # Separate tracks for sides A and B
        self.tape_length = 30 * 60  # Default: 30 minutes per side (60-minute tape)
        self.library = []
        self.current_usage = {"A": 0, "B": 0}
        self.library_file = "library.json"

        self.playback_active = False

        # Initialize pygame mixer
        mixer.init(48000, -16, 2, 2048, allowedchanges=0)

        # Create UI
        self.create_widgets()

        # Load library
        if(os.path.exists("library.json")):
            with open("library.json", "r") as file_:
                self.library = json.load(file_)
            for song in self.library:
                filepath, file, duration = song['path'], song['name'], song['duration']
                self.library_tree.insert("", "end", text=os.path.basename(os.path.split(filepath)[0]), values=(file, self.format_time(duration)))

    def create_widgets(self):
        # Tape length selection
        ttk.Label(self.root, text="Tape Length (minutes):").grid(row=0, column=0, padx=5, pady=5)
        self.tape_length_var = tk.IntVar(value=60)
        ttk.Combobox(
            self.root, textvariable=self.tape_length_var, values=[30, 60, 90, 120], state="readonly"
        ).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.root, text="Set", command=self.set_tape_length).grid(row=0, column=2, padx=5, pady=5)

        # Library and mixtape controls
        ttk.Button(self.root, text="Load Library", command=self.load_library).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(self.root, text="New Mixtape", command=self.new_mixtape).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.root, text="Save Mixtape", command=self.save_mixtape).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(self.root, text="Load Mixtape", command=self.load_mixtape).grid(row=1, column=3, padx=5, pady=5)
        ttk.Button(self.root, text="Export Mixtape", command=self.export_mixtape).grid(row=0, column=3, padx=5, pady=5)

        # Search bar
        ttk.Label(self.root, text="Search:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_library)
        ttk.Entry(self.root, textvariable=self.search_var).grid(row=2, column=1, padx=5, pady=5, sticky="we")

        # Library list
        ttk.Label(self.root, text="Music Library:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.library_frame = ttk.Frame(self.root)
        self.library_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.library_tree = ttk.Treeview(self.library_frame)
        self.library_tree["columns"] = ("name", "duration")
        self.library_tree.heading("#0", text="Folder", anchor="w")
        self.library_tree.heading("name", text="Name", anchor="w")
        self.library_tree.heading("duration", text="Duration", anchor="w")
        self.library_tree.pack(side="left", fill="both", expand=True)

        # Scrollbar for library
        library_scrollbar = ttk.Scrollbar(self.library_frame, orient="vertical", command=self.library_tree.yview)
        self.library_tree.configure(yscrollcommand=library_scrollbar.set)
        library_scrollbar.pack(side="right", fill="y")

        ttk.Button(self.root, text="Add to Side A", command=lambda: self.add_to_mixtape("A")).grid(row=5, column=0, padx=5, pady=5)
        ttk.Button(self.root, text="Add to Side B", command=lambda: self.add_to_mixtape("B")).grid(row=5, column=1, padx=5, pady=5)

        # Mixtape lists for sides A and B
        self.create_mixtape_side_ui("A", 2)
        self.create_mixtape_side_ui("B", 3)

        # Tape usage with progress bars
        self.usage_frame = ttk.Frame(self.root)
        self.usage_frame.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        self.usage_label_a = ttk.Label(self.usage_frame, text="Side A Usage:")
        self.usage_label_a.grid(row=0, column=0, sticky="w")
        self.usage_bar_a = ttk.Progressbar(self.usage_frame, length=200, mode="determinate")
        self.usage_bar_a.grid(row=0, column=1, padx=5)
        self.usage_label_b = ttk.Label(self.usage_frame, text="Side B Usage:")
        self.usage_label_b.grid(row=1, column=0, sticky="w")
        self.usage_bar_b = ttk.Progressbar(self.usage_frame, length=200, mode="determinate")
        self.usage_bar_b.grid(row=1, column=1, padx=5)

         # Playback progress 
        self.progress_frame = ttk.Frame(self.root)
        self.progress_frame.grid(row=8, column=0, columnspan=8, padx=5, pady=5, sticky="nsew")

        # Configurable playback progress label
        self.progress_label = ttk.Label(self.progress_frame, text="Playing: [Nothing is playing]")  # Configurable text
        self.progress_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

        # Progress bar itself
        self.progress_bar = ttk.Progressbar(self.progress_frame, length=400, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="we")

        # Configurable playback progress label
        self.total_progress_label = ttk.Label(self.progress_frame, text="Total Progress")  # Configurable text
        self.total_progress_label.grid(row=0, column=5, columnspan=4, sticky="w", padx=5, pady=(5, 0))

        # Total progress
        self.total_progress_bar = ttk.Progressbar(self.progress_frame, length=400, mode="determinate")
        self.total_progress_bar.grid(row=1, column=5, columnspan=4, padx=5, pady=5, sticky="we")

        # Playback controls
        ttk.Button(self.root, text="Play Side A", command=lambda: self.play_mixtape("A")).grid(row=7, column=0, padx=5, pady=5)
        ttk.Button(self.root, text="Play Side B", command=lambda: self.play_mixtape("B")).grid(row=7, column=1, padx=5, pady=5)
        ttk.Button(self.root, text="Stop Playback", command=self.stop_playback).grid(row=7, column=2, padx=5, pady=5)

    def create_mixtape_side_ui(self, side, column):
        ttk.Label(self.root, text=f"Side {side}:").grid(row=3, column=column, padx=5, pady=5, sticky="w")
        frame = ttk.Frame(self.root)
        frame.grid(row=4, column=column, padx=5, pady=5)

        listbox = tk.Listbox(frame, height=15, width=50)
        listbox.pack(side="left", fill="both", expand=True)
        setattr(self, f"side_{side.lower()}_listbox", listbox)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=5, column=column, padx=5, pady=5)
        ttk.Button(btn_frame, text="Remove", command=lambda: self.remove_from_mixtape(side)).pack(side="left")
        ttk.Button(btn_frame, text="Up", command=lambda: self.move_song(side, -1)).pack(side="left")
        ttk.Button(btn_frame, text="Down", command=lambda: self.move_song(side, 1)).pack(side="left")

    def set_tape_length(self):
        self.tape_length = self.tape_length_var.get() * 30  # Half the total for each side
        self.update_usage()

    def load_library(self):
        index_thread = threading.Thread(target=self.load_library_thread)
        index_thread.start()

    def load_library_thread(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.library = []
        self.library_tree.delete(*self.library_tree.get_children())

        loading_label = ttk.Label(self.root, text="Loading... Please wait")
        loading_label.grid(row=9, column=1, columnspan=4, pady=10)
        self.root.update()

        for root, _, files in os.walk(folder):
            for file in files:
                if file.endswith(".mp3") or file.endswith(".wav") or file.endswith(".flac"):
                    try:
                        filepath = os.path.join(root, file)
                        if file.endswith(".mp3"):
                            audio = MP3(filepath)
                        if file.endswith(".wav"):
                            audio = WAVE(filepath)
                        if file.endswith(".flac"):
                            audio = FLAC(filepath)
                        duration = audio.info.length
                        song_info = {"path": filepath, "name": file, "duration": duration}
                        self.library.append(song_info)
                        self.library_tree.insert("", "end", text=os.path.basename(os.path.split(filepath)[0]), values=(file, self.format_time(duration)))
                    except:
                        pass

        loading_label.destroy()

        # Save library for reuse
        with open(self.library_file, "w") as f:
            json.dump(self.library, f)

    def new_mixtape(self):
        self.mixtape = {"A": [], "B": []}
        self.side_a_listbox.delete(0, tk.END)
        self.side_b_listbox.delete(0, tk.END)
        self.current_usage = {"A": 0, "B": 0}
        self.update_usage()

    def save_mixtape(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not filepath:
            return

        with open(filepath, "w") as f:
            json.dump(self.mixtape, f)

        messagebox.showinfo("Save Mixtape", "Mixtape saved successfully!")

    def export_mixtape(self):
        path = filedialog.askdirectory()
        self.save_mixtape()

        for side in ["A", "B"]:
            for index, song in enumerate(self.mixtape[side]):
                shutil.copyfile(os.path.normpath(song['path']), os.path.join(path, "{}{} {}".format(side, index + 1, song['name'])))
        messagebox.showinfo("Export Mixtape", "Mixtape exported successfully!")
                

    def load_mixtape(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not filepath:
            return

        with open(filepath, "r") as f:
            self.mixtape = json.load(f)

        self.side_a_listbox.delete(0, tk.END)
        self.side_b_listbox.delete(0, tk.END)
        self.current_usage = {"A": 0, "B": 0}

        for side in ["A", "B"]:
            for song in self.mixtape[side]:
                listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
                listbox.insert(tk.END, f"{song['name']} ({self.format_time(song['duration'])})")
                self.current_usage[side] += song['duration']

        self.update_usage()

    def add_to_mixtape(self, side):
        selected = self.library_tree.selection()
        if not selected:
            return

        for item in selected:
            song_index = self.library_tree.item(item, "values")
            song = next((s for s in self.library if s["name"] == song_index[0]), None)
            if not song:
                continue

            self.mixtape[side].append(song)
            listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
            listbox.insert(tk.END, f"{song['name']} ({self.format_time(song['duration'])})")
            self.current_usage[side] += song['duration']

        if self.current_usage[side] > self.tape_length:
            messagebox.showwarning("Tape Full", f"Side {side} exceeds the maximum tape length!")
        self.update_usage()

    def remove_from_mixtape(self, side):
        listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
        selection = listbox.curselection()
        if not selection:
            return

        index = selection[0]
        song = self.mixtape[side][index]
        self.current_usage[side] -= song['duration']
        del self.mixtape[side][index]
        listbox.delete(index)
        self.update_usage()

    def move_song(self, side, direction):
        listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
        selection = listbox.curselection()
        if not selection:
            return

        index = selection[0]
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.mixtape[side]):
            return

        self.mixtape[side][index], self.mixtape[side][new_index] = (
            self.mixtape[side][new_index],
            self.mixtape[side][index],
        )

        listbox.delete(0, tk.END)
        for song in self.mixtape[side]:
            listbox.insert(tk.END, f"{song['name']} ({self.format_time(song['duration'])})")
        listbox.select_set(new_index)

    def filter_library(self, *args):
        search_term = self.search_var.get().lower()
        self.library_tree.delete(*self.library_tree.get_children())
        for song in self.library:
            if search_term in song['name'].lower():
                filepath, file, duration = song['path'], song['name'], song['duration']
                self.library_tree.insert("", "end", text=os.path.basename(os.path.split(filepath)[0]), values=(file, self.format_time(duration)))


    def play_mixtape(self, side):
        playback_thread = threading.Thread(target=self.play_mixtape_thread, args=[side])
        playback_thread.start()


    def play_mixtape_thread(self, side):
        playlist = self.mixtape[side]
        if not playlist:
            messagebox.showwarning("Playback", f"Side {side} is empty!")
            return

        self.stop_playback()  # Stop any ongoing playback
        self.playback_active = True

        total_time = 0
        current_time = 0
        for song in playlist:
            total_time += song['duration']
        
        for song in playlist:
            mixer.music.load(song['path'])
            mixer.music.play()
            while mixer.music.get_busy():
                if(self.playback_active):
                    self.progress_label.configure(text="Playing: {} {}/{}".format(os.path.split(song['path'])[1], self.format_time(mixer.music.get_pos() / 1000), self.format_time(song['duration'])))
                    self.progress_bar["value"] = 100 * (mixer.music.get_pos() / 1000) / song['duration']
                    self.total_progress_bar["value"] = 100 * (current_time + mixer.music.get_pos() / 1000) / total_time
                    continue
                else:
                    self.progress_label.configure(text="Playing: [Nothing is playing]")
                    self.progress_bar["value"] = 0
                    self.total_progress_bar["value"] = 0
                    break
            if(not self.playback_active):
                self.progress_label.configure(text="Playing: [Nothing is playing]")
                self.progress_bar["value"] = 0
                self.total_progress_bar["value"] = 0
                break
            current_time += song['duration']

    def stop_playback(self):
        self.playback_active = False
        mixer.music.stop()

    def format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        return f"{mins}:{secs:02}"


    def update_usage(self):
        for side in ["A", "B"]:
            usage = self.current_usage[side] / self.tape_length
            progress_bar = self.usage_bar_a if side == "A" else self.usage_bar_b
            progress_bar["value"] = usage * 100

            if usage <= 0.8:
                progress_bar["style"] = "Green.Horizontal.TProgressbar"
            elif usage <= 0.95:
                progress_bar["style"] = "Yellow.Horizontal.TProgressbar"
            else:
                progress_bar["style"] = "Red.Horizontal.TProgressbar"

        formatted_time_a = self.format_time(self.current_usage["A"])
        formatted_time_b = self.format_time(self.current_usage["B"])
        side_a_max = self.format_time(self.tape_length)
        side_b_max = self.format_time(self.tape_length)

        self.usage_label_a.config(text=f"Side A Usage: {formatted_time_a} / {side_a_max}")
        self.usage_label_b.config(text=f"Side B Usage: {formatted_time_b} / {side_b_max}")

    @staticmethod
    def format_time(seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"

if __name__ == "__main__":
    root = tk.Tk()
    app = MixtapeApp(root)

    # Progress bar styles
    style = ttk.Style()
    style.configure("Green.Horizontal.TProgressbar", foreground="green", background="green")
    style.configure("Yellow.Horizontal.TProgressbar", foreground="yellow", background="yellow")
    style.configure("Red.Horizontal.TProgressbar", foreground="red", background="red")

    root.mainloop()
