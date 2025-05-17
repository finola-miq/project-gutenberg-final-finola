# finola miqailla
# 04/29/2025

import re
import sqlite3
import tkinter as tk
from html.parser import HTMLParser
from tkinter import messagebox
from urllib.request import urlopen
from typing import List, Tuple

# --- Database Setup ---

conn = sqlite3.connect('project_gutenberg.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS book (
    id INTEGER PRIMARY KEY,
    title TEXT,
    link TEXT
)
''')


cursor.execute('''
CREATE TABLE IF NOT EXISTS word_frequencies (
    id INTEGER PRIMARY KEY,
    book_id INTEGER,
    word TEXT,
    frequency INTEGER,
    FOREIGN KEY (book_id) REFERENCES book(id)
)
''')

# --- HTML Parsing ---

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words = []
        self.extracted_title = ""
        self.title_found = False

    def handle_data(self, data):
        if not self.title_found and "title:" in data:
            match = re.search(r"title:\s*(.+)", data, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                self.extracted_title = extracted
                self.title_found = True


        # Collect all words
        self.words.extend(re.findall(r'\b\w+\b', data.lower()))


# --- Database Functions ---

def insert_book(title, link):
    cursor.execute("SELECT id FROM book WHERE title = ? AND link = ?", (title, link))
    result = cursor.fetchone()
    if result:
        return result[0]  # Return existing book ID
    else:
        cursor.execute("INSERT INTO book VALUES (NULL, ?, ?)", (title, link))
        conn.commit()
        return cursor.lastrowid



def insert_word_frequencies(book_id: int, frequencies: List[Tuple[str, int]]):
    cursor.execute("DELETE FROM word_frequencies WHERE book_id = ?", (book_id,))
    cursor.executemany(
        "INSERT INTO word_frequencies (book_id, word, frequency) VALUES (?, ?, ?)",
        [(book_id, word, freq) for word, freq in frequencies]
    )
    conn.commit()

def fetch_frequencies_by_title(title: str) -> List[Tuple[str, int]]:
    cursor.execute("SELECT id FROM book WHERE title = ?", (title,))
    result = cursor.fetchone()
    if not result:
        return []
    book_id = result[0]
    cursor.execute('''
        SELECT word, frequency 
        FROM word_frequencies 
        WHERE book_id = ?
        ORDER BY frequency DESC 
        LIMIT 10
    ''', (book_id,))
    return cursor.fetchall()

# --- GUI Functionality ---

def display_results(results: List[Tuple[str, int]]):
    results_box.delete("1.0", tk.END)
    if not results:
        results_box.insert(tk.END, "No results to display.")
    else:
        for word, freq in results:
            results_box.insert(tk.END, f"{word}: {freq}\n")

def search_local_title():
    title = title_entry.get().strip()
    if not title:
        messagebox.showwarning("Input Error", "Please enter a book title.")
        return
    results = fetch_frequencies_by_title(title)
    if results:
        display_results(results)
    else:
        messagebox.showinfo("Not Found", "Book was not found in the local database.")

def search_url_and_store():
    link = url_entry.get().strip()
    if not link:
        messagebox.showwarning("Input Error", "Please enter a URL.")
        return

    try:
        response = urlopen(link)
        html_text = response.read().decode('utf-8').lower()

        parser = MyHTMLParser()
        parser.feed(html_text)

        title = parser.extracted_title if parser.title_found else "Unknown Title"

        # Count word frequencies
        freq = {}
        for word in parser.words:
            freq[word] = freq.get(word, 0) + 1

        top_10 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]

        # Now pass the extracted title and link into insert_book
        book_id = insert_book(title, link)
        insert_word_frequencies(book_id, top_10)
        display_results(top_10)

    except Exception as e:
        display_results([(f"Error: {str(e)}", "")])

# --- GUI Setup ---

root = tk.Tk()
root.title("Project Gutenberg")

# Local search widgets
tk.Label(root, text="Input book title:").pack(pady=(10, 0))
title_entry = tk.Entry(root, width=40)
title_entry.pack(pady=(0, 10))
tk.Button(root, text="Fetch from local DB", command=search_local_title).pack()

# URL search widgets
tk.Label(root, text="Input URL:").pack(pady=(10, 0))
url_entry = tk.Entry(root, width=60)
url_entry.pack(pady=(0, 10))
tk.Button(root, text="Fetch from URL and store", command=search_url_and_store).pack()

# Output display
results_box = tk.Text(root, height=12, width=60)
results_box.pack(pady=(10, 10))

# Start GUI loop
root.mainloop()

# Finalize DB
conn.commit()
conn.close()
