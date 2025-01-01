import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
import sys
import winreg
import schedule
import time
import threading
from PIL import Image, ImageTk
import ctypes
from datetime import datetime
import webbrowser
import pyperclip
from urllib.parse import quote

class LoadingSpinner:
    def __init__(self, parent, size=20):
        self.parent = parent
        self.size = size
        self.canvas = tk.Canvas(parent, width=size, height=size, bg='#F0F4F8', highlightthickness=0)
        self.angle = 0
        self.drawing = None
        
    def start(self):
        self.canvas.pack(pady=2)
        self.draw()
        
    def stop(self):
        if self.drawing:
            self.canvas.after_cancel(self.drawing)
        self.canvas.pack_forget()
        
    def draw(self):
        self.canvas.delete("all")
        x = self.size/2
        y = self.size/2
        r = self.size/2 - 2
        
        start = self.angle
        extent = 270
        self.canvas.create_arc(2, 2, self.size-2, self.size-2, 
                             start=start, extent=extent, 
                             outline='#1E3F66', width=2, style='arc')
        
        self.angle = (self.angle + 10) % 360
        self.drawing = self.canvas.after(50, self.draw)

class BibleVerseWidget:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Bible Verse Widget")
        
        # Initialize variables
        self.verses_history = []
        self.current_index = -1
        self.is_transparent = False
        self.current_translation = "bible"
        
        # Available translations
        self.translations = {
            "KJV": "kjv",
            "WEB": "web",
            "BASIC": "basic-english",
            "BBE": "bbe",
            "ASV": "asv"
        }
        
        # Load saved data
        self.load_saved_data()

        self.setup_window()
        self.setup_ui()
        self.add_to_startup()
        
        # Start verse update thread
        self.update_thread = threading.Thread(target=self.schedule_verses, daemon=True)
        self.update_thread.start()
    
    def load_saved_data(self):
        # Load favorites
        try:
            with open('favorite_verses.json', 'r') as f:
                self.favorite_verses = json.load(f)
        except:
            self.favorite_verses = []

        # Load cached verses
        try:
            with open('cached_verses.json', 'r') as f:
                self.cached_verses = json.load(f)
        except:
            self.cached_verses = []

    def setup_window(self):
        self.always_on_top = False  # Default not on top
        self.window.attributes('-topmost', self.always_on_top, '-alpha', 0.9)
        self.window.overrideredirect(True)
        
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        self.widget_width = 300
        self.widget_height = 250
        x_position = screen_width - self.widget_width - 20
        y_position = 50
        
        self.window.geometry(f"{self.widget_width}x{self.widget_height}+{x_position}+{y_position}")

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.window.attributes('-topmost', self.always_on_top)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def on_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")

    def toggle_transparency(self):
        self.is_transparent = not self.is_transparent
        if self.is_transparent:
            self.window.attributes('-alpha', 0.5)
        else:
            self.window.attributes('-alpha', 0.9)

    def add_to_startup(self):
        if getattr(sys, 'frozen', False):
            app_path = sys.executable
        else:
            app_path = os.path.abspath(__file__)
            
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        try:
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, "BibleVerseWidget", 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(registry_key)
        except WindowsError:
            pass
    
        def load_favorites(self):
            try:
                with open('favorite_verses.json', 'r') as f:
                    return json.load(f)
            except:
                return []
            
    def setup_title_bar_buttons(self):
        close_button = tk.Button(self.title_bar, text='×', command=self.window.quit,
                            bg='#1E3F66', fg='white', bd=0, padx=5)
        close_button.pack(side=tk.RIGHT)
        
        settings_button = tk.Button(self.title_bar, text='⚙', command=self.toggle_transparency,
                                bg='#1E3F66', fg='white', bd=0, padx=5)
        settings_button.pack(side=tk.RIGHT)
        
        # Add always-on-top toggle button (optional)
        top_button = tk.Button(self.title_bar, text='📌', command=self.toggle_always_on_top,
                            bg='#1E3F66', fg='white', bd=0, padx=5)
        top_button.pack(side=tk.RIGHT)

    def save_favorites(self):
        with open('favorite_verses.json', 'w') as f:
            json.dump(self.favorite_verses, f)

    def load_cached_verses(self):
        try:
            with open('cached_verses.json', 'r') as f:
                return json.load(f)
        except:
            return []

    def save_cached_verses(self):
        with open('cached_verses.json', 'w') as f:
            json.dump(self.cached_verses, f)

    def setup_ui(self):
        self.main_frame = tk.Frame(self.window, bg='#F0F4F8')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.title_bar = tk.Frame(self.main_frame, bg='#1E3F66', height=30)
        self.title_bar.pack(fill=tk.X)
        self.title_bar.bind('<Button-1>', self.start_move)
        self.title_bar.bind('<B1-Motion>', self.on_move)
        
        self.setup_title_bar_buttons()
        
        self.translation_frame = tk.Frame(self.main_frame, bg='#F0F4F8')
        self.translation_frame.pack(fill=tk.X, padx=5)
        self.setup_translation_selector()
        
        self.verse_frame = tk.Frame(self.main_frame, bg='#F0F4F8')
        self.verse_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.verse_text = tk.Text(self.verse_frame, wrap=tk.WORD, height=5,
                                 font=('Georgia', 10), bg='#F0F4F8', relief=tk.FLAT)
        self.verse_text.pack(fill=tk.BOTH, expand=True)
        self.verse_text.configure(state='disabled')
        
        self.spinner = LoadingSpinner(self.verse_frame)
        
        self.action_frame = tk.Frame(self.main_frame, bg='#F0F4F8')
        self.action_frame.pack(fill=tk.X, padx=10, pady=5)
        self.setup_action_buttons()
        
        self.nav_frame = tk.Frame(self.main_frame, bg='#F0F4F8')
        self.nav_frame.pack(fill=tk.X, padx=10, pady=5)
        self.setup_navigation_buttons()
        
        self.update_verse()

    def setup_title_bar_buttons(self):
        close_button = tk.Button(self.title_bar, text='×', command=self.window.quit,
                               bg='#1E3F66', fg='white', bd=0, padx=5)
        close_button.pack(side=tk.RIGHT)
        
        settings_button = tk.Button(self.title_bar, text='⚙', command=self.toggle_transparency,
                                  bg='#1E3F66', fg='white', bd=0, padx=5)
        settings_button.pack(side=tk.RIGHT)

    def setup_translation_selector(self):
        tk.Label(self.translation_frame, text="Translation:", 
                bg='#F0F4F8').pack(side=tk.LEFT, padx=5)
        self.translation_var = tk.StringVar(value="KJV")
        translation_menu = ttk.Combobox(self.translation_frame, 
                                      textvariable=self.translation_var,
                                      values=list(self.translations.keys()),
                                      width=10,
                                      state="readonly")
        translation_menu.pack(side=tk.LEFT, padx=5)
        translation_menu.bind('<<ComboboxSelected>>', self.on_translation_change)

    def setup_action_buttons(self):
        self.fav_button = ttk.Button(self.action_frame, text="♡", 
                                    command=self.toggle_favorite, width=3)
        self.fav_button.pack(side=tk.LEFT, padx=2)
        
        self.share_button = ttk.Button(self.action_frame, text="Share", 
                                     command=self.show_share_options, width=6)
        self.share_button.pack(side=tk.LEFT, padx=2)
        
        '''self.offline_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.action_frame, text="Offline", 
                       variable=self.offline_var,
                       command=self.toggle_offline_mode).pack(side=tk.RIGHT, padx=2)'''

    def setup_navigation_buttons(self):
        self.prev_button = ttk.Button(self.nav_frame, text="←", 
                                    command=self.previous_verse)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = ttk.Button(self.nav_frame, text="→", 
                                    command=self.next_verse)
        self.next_button.pack(side=tk.RIGHT, padx=5)

    def show_share_options(self):
        share_window = tk.Toplevel(self.window)
        share_window.title("Share Verse")
        share_window.geometry("200x150")
        
        ttk.Button(share_window, text="Copy to Clipboard", 
                  command=lambda: self.copy_to_clipboard(share_window)).pack(pady=5)
        
        ttk.Button(share_window, text="Share to Twitter", 
                  command=lambda: self.share_to_twitter(share_window)).pack(pady=5)
        ttk.Button(share_window, text="Share to Facebook", 
                  command=lambda: self.share_to_facebook(share_window)).pack(pady=5)

    def copy_to_clipboard(self, share_window):
        verse_text = self.verse_text.get(1.0, tk.END).strip()
        pyperclip.copy(verse_text)
        messagebox.showinfo("Success", "Verse copied to clipboard!")
        share_window.destroy()

    def share_to_twitter(self, share_window):
        verse_text = self.verse_text.get(1.0, tk.END).strip()
        tweet_text = quote(f"{verse_text[:200]}...")
        webbrowser.open(f"https://twitter.com/intent/tweet?text={tweet_text}")
        share_window.destroy()

    def share_to_facebook(self, share_window):
        verse_text = self.verse_text.get(1.0, tk.END).strip()
        fb_text = quote(verse_text)
        webbrowser.open(f"https://www.facebook.com/sharer/sharer.php?u=&quote={fb_text}")
        share_window.destroy()

    def toggle_favorite(self):
        current_verse = self.verse_text.get(1.0, tk.END).strip()
        if current_verse in self.favorite_verses:
            self.favorite_verses.remove(current_verse)
            self.fav_button.configure(text="♡")
        else:
            self.favorite_verses.append(current_verse)
            self.fav_button.configure(text="♥")
        self.save_favorites()

    '''def toggle_offline_mode(self):
        if self.offline_var.get() and not self.cached_verses:
            messagebox.showwarning("Warning", "No cached verses available. Will download some verses first.")
            self.cache_verses()'''

    def cache_verses(self):
        self.spinner.start()
        for _ in range(50):
            try:
                verse = self.get_random_verse(use_cache=False)
                if verse not in self.cached_verses:
                    self.cached_verses.append(verse)
            except:
                continue
        self.save_cached_verses()
        self.spinner.stop()

    def get_random_verse(self, use_cache=None):
        '''if use_cache is None:
            use_cache = self.offline_var.get()'''

        if use_cache and self.cached_verses:
            return random.choice(self.cached_verses)

        try:
            self.spinner.start()
            response = requests.get(f"https://bible-api.com/?random=verse")
            data = response.json()
            verse = f"{data['text']}\n\n- {data['reference']} ({self.translation_var.get()})"
            self.spinner.stop()
            return verse
        except Exception as e:
            self.spinner.stop()
            print(f"Error fetching verse: {e}")
            return "For God so loved the world that he gave his one and only Son.\n\n- John 3:16 (KJV)"

    def schedule_verses(self):
        schedule.every(2).minutes.do(self.update_verse)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def on_translation_change(self, event=None):
        self.update_verse()

    def update_verse(self):
        verse = self.get_random_verse()
        self.verses_history.append(verse)
        self.current_index = len(self.verses_history) - 1
        self.display_verse(verse)

    def display_verse(self, verse):
        self.verse_text.configure(state='normal')
        self.verse_text.delete(1.0, tk.END)
        self.verse_text.insert(tk.END, verse)
        self.verse_text.configure(state='disabled')
        
        if verse.strip() in self.favorite_verses:
            self.fav_button.configure(text="♥")
        else:
            self.fav_button.configure(text="♡")

    def previous_verse(self):
        self.update_verse()

    def next_verse(self):
        self.update_verse()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = BibleVerseWidget()
    app.run()