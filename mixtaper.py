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
import random
import time

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
        if os.path.exists("library.json"):
            with open("library.json", "r") as file_:
                saved_data = json.load(file_)
                self.library = saved_data.get('songs', [])
                self.library_root = saved_data.get('root_folder', '')
            
            self.library_tree.delete(*self.library_tree.get_children())
            
            if self.library:
                # Group by folder structure using relative paths
                folder_nodes = {}
                
                for song in self.library:
                    # Get relative path from library root
                    if self.library_root and 'folder' in song:
                        full_folder_path = song['folder']
                        # Calculate relative path to library root
                        try:
                            if full_folder_path.startswith(self.library_root):
                                relative_path = os.path.relpath(full_folder_path, self.library_root)
                            else:
                                relative_path = os.path.basename(full_folder_path)
                        except:
                            relative_path = os.path.basename(full_folder_path)
                    else:
                        # Fallback: just use the folder name
                        relative_path = os.path.basename(os.path.dirname(song['path']))
                    
                    # Handle root folder case
                    if relative_path == '.':
                        relative_path = os.path.basename(self.library_root) if self.library_root else "Music"
                    
                    folder_parts = relative_path.split(os.sep)
                    current_parent = ""
                    
                    # Build folder hierarchy
                    for i, part in enumerate(folder_parts):
                        parent_path = os.sep.join(folder_parts[:i])
                        current_path = os.sep.join(folder_parts[:i+1])
                        
                        if current_path not in folder_nodes:
                            if i == 0:
                                node = self.library_tree.insert("", "end", text=part, values=("", ""))
                            else:
                                parent_node = folder_nodes[parent_path]
                                node = self.library_tree.insert(parent_node, "end", text=part, values=("", ""))
                            folder_nodes[current_path] = node
                    
                    # Add song to folder
                    parent_node = folder_nodes.get(relative_path, "")
                    if parent_node:
                        self.library_tree.insert(
                            parent_node, "end", 
                            text="",
                            values=(song['name'], self.format_time(song['duration'])),
                            tags=("song",)
                        )
                
                self.library_tree.tag_configure("song", foreground="black")
                # Expand first level folders
                for child in self.library_tree.get_children():
                    self.library_tree.item(child, open=False)
        self.set_tape_length()

    def create_widgets(self):
        # Configure grid weights for responsive layout
        self.root.grid_rowconfigure(4, weight=1)  # Main content row
        self.root.grid_rowconfigure(8, weight=0)  # Progress bars row
        self.root.grid_columnconfigure(0, weight=1)  # Library column
        self.root.grid_columnconfigure(2, weight=1)  # Side A column  
        self.root.grid_columnconfigure(4, weight=1)  # Side B column

        # Tape length selection
        ttk.Label(self.root, text="Tape Length (minutes):").grid(row=0, column=0, padx=5, pady=5)
        self.tape_length_var = tk.StringVar(value="60")

        # Frame for tape length controls
        tape_frame = ttk.Frame(self.root)
        tape_frame.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        # Combobox with common values
        tape_combo = ttk.Combobox(
            tape_frame, 
            textvariable=self.tape_length_var, 
            values=[30, 45, 60, 90, 120, 180],
            state="normal",
            width=8
        )
        tape_combo.pack(side="left", padx=(0, 5))

        # Set button
        ttk.Button(tape_frame, text="Set", command=self.set_tape_length).pack(side="left")

        # Real-time side length display
        self.side_length_label = ttk.Label(tape_frame, text="(30:00 per side)")
        self.side_length_label.pack(side="left", padx=10)

        # Validation for numeric input only
        def validate_tape_length(input):
            if input == "" or input.isdigit():
                return True
            else:
                return False

        vcmd = (self.root.register(validate_tape_length), '%P')
        tape_combo.configure(validate="key", validatecommand=vcmd)

        # Update side length display when value changes
        def update_side_display(*args):
            try:
                minutes = int(self.tape_length_var.get())
                side_minutes = minutes // 2
                self.side_length_label.config(text=f"({side_minutes}:00 per side)")
            except ValueError:
                self.side_length_label.config(text="(Invalid)")

        self.tape_length_var.trace("w", update_side_display)

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

        # Library list - MAKE EXPANDABLE
        ttk.Label(self.root, text="Music Library:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.library_frame = ttk.Frame(self.root)
        self.library_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.library_frame.grid_rowconfigure(0, weight=1)
        self.library_frame.grid_columnconfigure(0, weight=1)

        # Create Treeview with hierarchy support
        self.library_tree = ttk.Treeview(self.library_frame, columns=("name", "duration"), show="tree headings")
        self.library_tree.heading("#0", text="Folder Structure", anchor="w")
        self.library_tree.heading("name", text="Name", anchor="w")
        self.library_tree.heading("duration", text="Duration", anchor="w")

        # Configure column widths
        self.library_tree.column("#0", width=200)
        self.library_tree.column("name", width=150)
        self.library_tree.column("duration", width=80)

        self.library_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for library
        library_scrollbar = ttk.Scrollbar(self.library_frame, orient="vertical", command=self.library_tree.yview)
        self.library_tree.configure(yscrollcommand=library_scrollbar.set)
        library_scrollbar.grid(row=0, column=1, sticky="ns")

        # Button frame for library actions 
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

        ttk.Button(button_frame, text="Add to Side A", command=lambda: self.add_to_mixtape("A")).pack(side="left", padx=40)
        ttk.Button(button_frame, text="Add to Side B", command=lambda: self.add_to_mixtape("B")).pack(side="left", padx=40)
        ttk.Button(button_frame, text="Autobalance Sides", command=self.auto_balance).pack(side="left", padx=40)
        ttk.Button(button_frame, text="Add Silence", command=self.add_silence).pack(side="left", padx=40)

        # Mixtape sides with consolidated controls in the middle - MAKE EXPANDABLE
        self.create_mixtape_side_ui("A", 2)  # Column 2 for Side A

        # Consolidated controls column (column 3 - between A and B)
        controls_frame = ttk.Frame(self.root)
        controls_frame.grid(row=4, column=3, padx=10, pady=5, sticky="ns")

        # Swap button (big and prominent)
        ttk.Button(controls_frame, text="⇄\nSwap", command=self.swap_sides, width=6).pack(pady=5)

        # Remove button
        ttk.Button(controls_frame, text="Remove", command=self.remove_selected).pack(pady=5)

        # Move up/down buttons
        move_frame = ttk.Frame(controls_frame)
        move_frame.pack(pady=5)
        ttk.Button(move_frame, text="↑", command=lambda: self.move_selected(-1), width=3).pack(side="left", padx=2)
        ttk.Button(move_frame, text="↓", command=lambda: self.move_selected(1), width=3).pack(side="left", padx=2)

        self.create_mixtape_side_ui("B", 4)  # Column 4 for Side B

        # Tape usage with progress bars
        self.usage_frame = ttk.Frame(self.root)
        self.usage_frame.grid(row=6, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")
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
        self.progress_label = ttk.Label(self.progress_frame, text="Playing: [Nothing is playing]")
        self.progress_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

        # Progress bar itself
        self.progress_bar = ttk.Progressbar(self.progress_frame, length=400, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="we")

        # Configurable playback progress label
        self.total_progress_label = ttk.Label(self.progress_frame, text="Total Progress")
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
        frame.grid(row=4, column=column, padx=5, pady=5, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Enable extended selection for multiple items - MAKE EXPANDABLE
        listbox = tk.Listbox(frame, height=15, width=50, selectmode=tk.EXTENDED)
        listbox.grid(row=0, column=0, sticky="nsew")
        setattr(self, f"side_{side.lower()}_listbox", listbox)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def set_tape_length(self):
        try:
            tape_minutes = int(self.tape_length_var.get())

            if tape_minutes < 1:
                messagebox.showerror("Invalid Length", "Tape length must be at least 1 minute!")
                return
            if tape_minutes > 360:
                messagebox.showerror("Invalid Length", "Tape length cannot exceed 360 minutes (6 hours)!")
                return

            self.tape_length = tape_minutes * 30  # Half the total for each side
            self.tape_length_var.set(str(tape_minutes))
            self.update_usage()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for tape length!")

    def load_library(self):
        index_thread = threading.Thread(target=self.load_library_thread)
        index_thread.start()

    def load_library_thread(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.library = []
        self.library_root = folder  # Store the root folder
        self.library_tree.delete(*self.library_tree.get_children())

        loading_label = ttk.Label(self.root, text="Loading... Please wait")
        loading_label.grid(row=9, column=1, columnspan=4, pady=10)
        self.root.update()

        folder_nodes = {}
        all_songs = []

        for root_dir, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith((".mp3", ".wav", ".flac")):
                    try:
                        filepath = os.path.join(root_dir, file)
                        if file.lower().endswith(".mp3"):
                            audio = MP3(filepath)
                        elif file.lower().endswith(".wav"):
                            audio = WAVE(filepath)
                        elif file.lower().endswith(".flac"):
                            audio = FLAC(filepath)

                        duration = audio.info.length

                        # Calculate relative path from library root
                        relative_path = os.path.relpath(root_dir, folder)
                        if relative_path == '.':
                            # This is the root folder itself
                            display_folder = os.path.basename(folder)
                        else:
                            display_folder = relative_path

                        song_info = {
                            "path": filepath, 
                            "name": file, 
                            "duration": duration,
                            "folder": root_dir  # Store full path for reference
                        }
                        self.library.append(song_info)
                        all_songs.append(song_info)

                        # Build folder hierarchy using relative paths
                        current_parent = ""
                        path_parts = display_folder.split(os.sep)

                        for i, part in enumerate(path_parts):
                            parent_path = os.sep.join(path_parts[:i])
                            current_path = os.sep.join(path_parts[:i+1])

                            if current_path not in folder_nodes:
                                if i == 0:
                                    node = self.library_tree.insert("", "end", text=part, values=("", ""))
                                else:
                                    parent_node = folder_nodes[parent_path]
                                    node = self.library_tree.insert(parent_node, "end", text=part, values=("", ""))
                                folder_nodes[current_path] = node

                        # Add song to the appropriate folder
                        parent_node = folder_nodes.get(display_folder, "")
                        if parent_node:
                            self.library_tree.insert(
                                parent_node, "end", 
                                text="",
                                values=(file, self.format_time(duration)),
                                tags=("song",)
                            )

                    except Exception as e:
                        print(f"Error loading {file}: {e}")
                        continue

        self.library_tree.tag_configure("song", foreground="black")

        # Expand the first level of folders
        for child in self.library_tree.get_children():
            self.library_tree.item(child, open=False)

        loading_label.destroy()

        # Save library for reuse - now including root folder
        library_data = {
            'songs': self.library,
            'root_folder': self.library_root
        }
        with open(self.library_file, "w") as f:
            json.dump(library_data, f)

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
                if song['is_silence'] == False:
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

    def add_to_mixtape(self, side, song=None, supressWarning=False):
        if song is None:
            selected = self.library_tree.selection()
            if not selected:
                return

            for item in selected:
                item_values = self.library_tree.item(item, "values")
                # Skip folder nodes (they have empty name values)
                if not item_values or not item_values[0]:
                    continue

                song_name = item_values[0]
                song = next((s for s in self.library if s["name"] == song_name), None)
                if song is None:
                    continue

                self.mixtape[side].append(song)
                listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
                listbox.insert(tk.END, f"{song['name']} ({self.format_time(song['duration'])})")
                self.current_usage[side] += song['duration']
        else:
            # Existing code for direct song addition
            self.mixtape[side].append(song)
            listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
            listbox.insert(tk.END, f"{song['name']} ({self.format_time(song['duration'])})")
            self.current_usage[side] += song['duration']

        if self.current_usage[side] > self.tape_length and not supressWarning:
            messagebox.showwarning("Tape Full", f"Side {side} exceeds the maximum tape length!")
        self.update_usage()

    def remove_from_mixtape(self, side, song=None):
        listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
    
        if song is None:
            # Handle multiple selections
            selected_indices = listbox.curselection()
            if not selected_indices:
                return
            
            # Remove from highest index to lowest to avoid index shifting issues
            selected_indices = sorted(selected_indices, reverse=True)
            for index in selected_indices:
                song = self.mixtape[side][index]
                self.current_usage[side] -= song['duration']
                del self.mixtape[side][index]
                listbox.delete(index)
        else:
            # Single song removal (for internal use)
            index = self.mixtape[side].index(song)
            self.current_usage[side] -= song['duration']
            del self.mixtape[side][index]
            listbox.delete(index)
        
        self.update_usage()

    def move_song(self, side, direction):
        listbox = self.side_a_listbox if side == "A" else self.side_b_listbox
        selected_indices = listbox.curselection()

        if not selected_indices:
            return

        # For multiple selection, we'll move the entire block
        if direction == -1:  # Moving up
            # Start from the topmost selected item
            min_index = min(selected_indices)
            if min_index == 0:
                return  # Can't move above the top

            # Move each selected item up
            for index in sorted(selected_indices):
                if index > 0:
                    self.mixtape[side][index], self.mixtape[side][index-1] = (
                        self.mixtape[side][index-1],
                        self.mixtape[side][index],
                    )

        else:  # Moving down
            # Start from the bottommost selected item
            max_index = max(selected_indices)
            if max_index >= len(self.mixtape[side]) - 1:
                return  # Can't move below the bottom

            # Move each selected item down (from bottom to top)
            for index in sorted(selected_indices, reverse=True):
                if index < len(self.mixtape[side]) - 1:
                    self.mixtape[side][index], self.mixtape[side][index+1] = (
                        self.mixtape[side][index+1],
                        self.mixtape[side][index],
                    )

        # Refresh the listbox
        listbox.delete(0, tk.END)
        for song in self.mixtape[side]:
            listbox.insert(tk.END, f"{song['name']} ({self.format_time(song['duration'])})")

        # Restore selection
        if direction == -1:
            new_indices = [i-1 for i in selected_indices if i > 0]
        else:
            new_indices = [i+1 for i in selected_indices if i < len(self.mixtape[side]) - 1]

        for index in new_indices:
            listbox.select_set(index)

    def remove_selected(self):
        """Remove selected songs from whichever side they're on"""
        selected_a = self.side_a_listbox.curselection()
        selected_b = self.side_b_listbox.curselection()

        if selected_a:
            self.remove_from_mixtape("A")
        elif selected_b:
            self.remove_from_mixtape("B")
        else:
            messagebox.showinfo("Remove", "Please select songs from either Side A or Side B to remove.")

    def move_selected(self, direction):
        """Move selected songs up or down on whichever side they're on"""
        selected_a = self.side_a_listbox.curselection()
        selected_b = self.side_b_listbox.curselection()

        if selected_a:
            self.move_song("A", direction)
        elif selected_b:
            self.move_song("B", direction)
        else:
            messagebox.showinfo("Move", "Please select songs from either Side A or Side B to move.")

    def filter_library(self, *args):
        search_term = self.search_var.get().lower()

        if not search_term:
            # If no search term, restore full hierarchy
            self.library_tree.delete(*self.library_tree.get_children())
            # We'd need to rebuild from self.library, but for simplicity,
            # let's just reload the library when search is cleared
            if hasattr(self, '_original_library'):
                self.library_tree.delete(*self.library_tree.get_children())
                for song in self._original_library:
                    # Rebuild logic would go here
                    pass
            return

        # Store original library if first search
        if not hasattr(self, '_original_library'):
            self._original_library = self.library.copy()

        # Clear and show only matching songs
        self.library_tree.delete(*self.library_tree.get_children())

        for song in self._original_library:
            if search_term in song['name'].lower():
                # Show matching songs in a flat list during search
                self.library_tree.insert(
                    "", "end", 
                    text=os.path.basename(os.path.dirname(song['path'])),
                    values=(song['name'], self.format_time(song['duration'])),
                    tags=("song",)
                )


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
            # Check if this is a silence track
            if song.get('is_silence', False):
                # Handle silence - show progress but don't play audio
                silence_duration = song['duration']
                start_time = time.time()

                self.progress_label.configure(text=f"Playing: {song['name']}")

                while time.time() - start_time < silence_duration and self.playback_active:
                    elapsed = time.time() - start_time
                    self.progress_bar["value"] = 100 * (elapsed / silence_duration)
                    self.total_progress_bar["value"] = 100 * (current_time + elapsed) / total_time
                    self.root.update()
                    time.sleep(0.1)  # Small delay to prevent high CPU usage

                if not self.playback_active:
                    break

            else:
                # Normal audio playback
                mixer.music.load(song['path'])
                mixer.music.play()
                while mixer.music.get_busy():
                    if self.playback_active:
                        self.progress_label.configure(text="Playing: {} {}/{}".format(
                            os.path.split(song['path'])[1], 
                            self.format_time(mixer.music.get_pos() / 1000), 
                            self.format_time(song['duration'])
                        ))
                        self.progress_bar["value"] = 100 * (mixer.music.get_pos() / 1000) / song['duration']
                        self.total_progress_bar["value"] = 100 * (current_time + mixer.music.get_pos() / 1000) / total_time
                        continue
                    else:
                        break
                    
            if not self.playback_active:
                break

            current_time += song['duration']
    
        # Reset UI after playback finishes
        if self.playback_active:
            self.progress_label.configure(text="Playing: [Nothing is playing]")
            self.progress_bar["value"] = 0
            self.total_progress_bar["value"] = 0
            self.playback_active = False

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

    def auto_balance(self):
        totalList = []

        for side in self.mixtape:
            listbox = self.side_a_listbox if side == "A" else self.side_b_listbox 
            initialLength = len(self.mixtape[side])
            for index in range(initialLength):
                reverse_index = initialLength -1 - index
                song = self.mixtape[side][reverse_index]
                totalList.append(song)
                self.remove_from_mixtape(side, song)

        dur_a = 0
        dur_b = 0
        best_ratio = 0
        best_list = []
        iter = 0
        while(True):
            newList = []
            for song in totalList:
                if dur_a < dur_b:
                    dur_a += song['duration']
                    newList.append(['A', song])
                else:
                    dur_b += song['duration']
                    newList.append(['B', song])
            ratio = dur_a / dur_b
            if(abs(ratio - 1) < abs(best_ratio - 1)):
                best_ratio = ratio
                best_list = []
                for entry in newList:
                    best_list.append(entry)

            if (0.99995 > ratio or ratio > 1.00005) and iter < 1000:
                dur_a = 0
                dur_b = 0
                iter += 1
                newList = []
                random.shuffle(totalList)
                continue
            else:
                break

        for entry in best_list:
            self.add_to_mixtape(entry[0], entry[1], supressWarning=True)
    
    def add_silence(self):
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title("Add Silence")
        popup.geometry("300x150")
        popup.transient(self.root)
        popup.grab_set()

        # Side selection
        ttk.Label(popup, text="Select Side:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        side_var = tk.StringVar(value="A")
        ttk.Combobox(popup, textvariable=side_var, values=["A", "B"], state="readonly").grid(row=0, column=1, padx=5, pady=5)

        # Silence duration
        ttk.Label(popup, text="Silence Duration (seconds):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        duration_var = tk.StringVar(value="5")
        duration_entry = ttk.Entry(popup, textvariable=duration_var)
        duration_entry.grid(row=1, column=1, padx=5, pady=5)

        # Validation function
        def validate_duration():
            try:
                duration = float(duration_var.get())
                if duration <= 0:
                    messagebox.showerror("Invalid Duration", "Duration must be positive!")
                    return False
                return True
            except ValueError:
                messagebox.showerror("Invalid Duration", "Please enter a valid number!")
                return False
        
        # Add button
        def add_silence_track():
            if validate_duration():
                side = side_var.get()
                duration = float(duration_var.get())
                
                # Create a "silence track" entry
                silence_track = {
                    "path": f"silence_{duration}s",  # Special identifier
                    "name": f"[Silence: {duration}s]",
                    "duration": duration,
                    "is_silence": True  # Flag to identify silence tracks
                }
                
                # Add to mixtape
                self.add_to_mixtape(side, silence_track, supressWarning=True)
                popup.destroy()
        
        ttk.Button(popup, text="Add Silence", command=add_silence_track).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Bind Enter key to add silence
        popup.bind('<Return>', lambda e: add_silence_track())
        duration_entry.focus()

    def swap_sides(self):
        """Move selected songs from one side to the other"""
        selected_a = self.side_a_listbox.curselection()
        selected_b = self.side_b_listbox.curselection()

        # Count how many sides have selections
        selections = sum(1 for sel in [selected_a, selected_b] if sel)

        if selections == 0:
            messagebox.showinfo("Swap Sides", "Please select songs from either Side A or Side B to swap.")
            return
        elif selections > 1:
            messagebox.showwarning("Swap Sides", "Please select songs from only one side at a time.")
            return

        if selected_a:
            # Handle multiple selections from Side A
            selected_indices = sorted(selected_a, reverse=True)  # Remove from highest index first
            swapped_songs = []

            for index in selected_indices:
                song = self.mixtape["A"][index]
                swapped_songs.append(song)
                self.remove_from_mixtape("A", song)

            # Add all swapped songs to Side B
            for song in swapped_songs:
                self.add_to_mixtape("B", song, supressWarning=True)

            # Select the swapped songs in Side B
            self.side_b_listbox.selection_clear(0, tk.END)
            for i in range(len(swapped_songs)):
                new_index = len(self.mixtape["B"]) - len(swapped_songs) + i
                self.side_b_listbox.select_set(new_index)
            if swapped_songs:
                self.side_b_listbox.see(len(self.mixtape["B"]) - 1)

        elif selected_b:
            # Handle multiple selections from Side B
            selected_indices = sorted(selected_b, reverse=True)  # Remove from highest index first
            swapped_songs = []

            for index in selected_indices:
                song = self.mixtape["B"][index]
                swapped_songs.append(song)
                self.remove_from_mixtape("B", song)

            # Add all swapped songs to Side A
            for song in swapped_songs:
                self.add_to_mixtape("A", song, supressWarning=True)

            # Select the swapped songs in Side A
            self.side_a_listbox.selection_clear(0, tk.END)
            for i in range(len(swapped_songs)):
                new_index = len(self.mixtape["A"]) - len(swapped_songs) + i
                self.side_a_listbox.select_set(new_index)
            if swapped_songs:
                self.side_a_listbox.see(len(self.mixtape["A"]) - 1)

    def on_closing(self):
        # Stop any active playback
        self.stop_playback()

        # Wait a moment for playback threa
        self.root.after(100, self.quit_app)

    def quit_app(self):
        if mixer.get_init():
            mixer.quit()
        self.root.destroy()

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
    style.configure("Treeview", indent=15)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.mainloop()