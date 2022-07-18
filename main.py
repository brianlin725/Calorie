from ctypes import alignment
from mailbox import mboxMessage
from pathlib import Path
from tkinter import *
import tkinter
from tkinter import filedialog
import customtkinter
from PIL import Image, ImageTk
from tkinter import messagebox, ttk
import sqlite3
import os
from googletrans import Translator
from numpy import save
import requests
import copy
import json

customtkinter.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class searchItem:
    def __init__(self, name, kcal, note, source):
        self.name = name
        self.kcal = kcal
        self.note = note
        self.source = source

    def __eq__(self,other):
        return self.name == other.name and self.kcal == other.kcal and self.note == other.note

class Item:
    def __init__(self, name, quantity, unit, p100g):
        self.name = name
        self.quantity = quantity
        self.unit = unit
        self.p100g = p100g


        #units = ["毫克","克","公斤","兩","斤","磅","盎司"]
        units = {"mg": 0.001, "g": 1, "kg": 1000, "liang": 37.5, "jin": 600, "lb": 453.592, "oz": 28.3495}
        f_quantity = float(quantity)

        self.quantityGram = round(f_quantity*units[self.unit],2)

    def setQuantity(self, quantity):
        self.quantity = quantity

    def setUnit(self, unit):
        self.unit = unit

    def setp100g(self, g):
        self.p100g = g


class App(customtkinter.CTk):
    global PATH
    PATH = os.path.dirname(os.path.realpath(__file__))

    WIDTH = 670
    HEIGHT = 550
    global itemList

    def __init__(self):
        super().__init__()
        self.itemList = []
        # Setting up window
        self.geometry(f"{App.WIDTH}x{App.HEIGHT}")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)  # call .on_closing() when app gets closed
        self.title("未儲存 - Calorie")
        self.iconbitmap(os.path.join(PATH, "icon.ico"))

        # Connecting to database
        conn = sqlite3.connect(os.path.join(PATH, "saved_items"))
        c = conn.cursor()
        self.currDir = ""
        self.save = True

        # Shortcuts
        self.bind('<Control-s>', self.saveFile)

        # Check if table exists
        c.execute(''' SELECT name FROM sqlite_master WHERE type='table' AND name='items' ''')
        try:
            result = c.fetchone()[0]
        except TypeError:
            c.execute("""CREATE TABLE items (
                name text,
                cal real
            )
            """)
            conn.commit()
        conn.close()

        # Adding frames
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frameTool = customtkinter.CTkFrame(master = self, width = 75, corner_radius=0)
        self.frameTool.grid(row = 0, column = 0, sticky = "nese", rowspan = 2)

        # Frame for calculated Data and entering
        self.frameTotal = customtkinter.CTkFrame(master = self, width = 75, height = 85, corner_radius = 10)
        self.frameTotal.grid(row = 1, column = 1, sticky = "nswe", pady = 5, padx = 5)

        self.currP100G = tkinter.StringVar()
        self.currP100G.set(f"Kcal/100g: {self.kcalP100G(self.itemList)}")
        
        self.currKcal = tkinter.StringVar()
        self.currKcal.set(f"總卡路里: {self.totalKCal(self.itemList)}")

        self.currCalculatedKcal = customtkinter.StringVar()
        self.currCalculatedKcal.set(f"總卡路里計算: {self.calculateKcal(0, self.itemList)}")

        self.label_KcalP100G = Label(master=self.frameTotal,
                                              textvariable = self.currP100G,
                                              font = ("Roboto Medium", 9),
                                              background = "#D7D7D8")  # font name and size in px
        self.label_KcalP100G.grid(row = 1, column = 3, padx = 5, pady = (4,5), sticky = "nswe")

        self.label_TotKcal = Label(master=self.frameTotal,
                                              textvariable = self.currKcal, 
                                              font = ("Roboto Medium", 9),
                                              background = "#D7D7D8")  # font name and size in px
        self.label_TotKcal.grid(row = 1, column = 2, padx = 5, pady = (4,5), sticky = "nswe")

        self.label_TotKcal = Label(master=self.frameTotal,
                                              textvariable = self.currCalculatedKcal,
                                              font=("Roboto Medium", 9),
                                              background = "#D7D7D8")  # font name and size in px
        self.label_TotKcal.grid(row = 1, column = 1, padx = (1,5), pady = (4,5), sticky = "nswe")

        self.entry_CalculateKcal = customtkinter.CTkEntry(master = self.frameTotal, width = 60)
        self.entry_CalculateKcal.grid(row = 1, column = 0, padx = (5,0), pady = (4,5), sticky = "nswe")
        self.entry_CalculateKcal.config(justify = "right")
        
        # Updates the totalKcal based on the number entered
        def calculateUpdate(event):
            if len(self.entry_CalculateKcal.get()) == 0:
                self.currCalculatedKcal.set(f"總卡路里計算: {self.calculateKcal(0, self.itemList)}")
            else:
                self.currCalculatedKcal.set(f"總卡路里計算: {self.calculateKcal(self.entry_CalculateKcal.get(), self.itemList)}")
        self.entry_CalculateKcal.bind("<KeyRelease>", calculateUpdate)

        #self.frame_right = customtkinter.CTkFrame(master=self)
        #self.frame_right.grid(row=0, column=1, sticky="nswe", padx=20, pady=20)
        #self.frame_right.rowconfigure(0, weight=1)
        #self.frame_right.columnconfigure(1, weight = 1)

        # Creating Treeview
        self.itemTree = ttk.Treeview(self, selectmode = "browse")
        self.itemTree["columns"] = ["item", "quantity", "unit", "per100gram"]
        ttk.Style().configure('Treeview', rowheight = 26)

        # formatting column
        self.itemTree.column("#0", width = 0, stretch = NO)
        self.itemTree.column("item", anchor = W, width = 120)
        self.itemTree.column("quantity", anchor = E, width = 70)
        self.itemTree.column("unit", anchor = W, width = 70)
        self.itemTree.column("per100gram", anchor = W, width = 70)

        # Treeview headings
        self.itemTree.heading("#0", text = "", anchor = W)
        self.itemTree.heading("item", text = "樣品名稱", anchor = W)
        self.itemTree.heading("quantity", text = "量", anchor = W)
        self.itemTree.heading("unit", text = "單位", anchor = CENTER)
        self.itemTree.heading("per100gram", text = "卡路里", anchor = W)

        self.itemTree.grid(row = 0, column = 1, sticky = "nswe", padx = 10, pady = (10,5))

        self.itemTree.bind("<Double-Button-1>", self.edit)
        self.itemTree.bind("<Delete>", self.removeElement)

        # configure grid layout (1x11)
        self.frameTool.grid_rowconfigure(0, minsize=10)   # empty row with minsize as spacing
        self.frameTool.grid_rowconfigure(5, weight=1)  # empty row as spacing
        self.frameTool.grid_rowconfigure(8, minsize=20)    # empty row with minsize as spacing
        self.frameTool.grid_rowconfigure(11, minsize=10)  # empty row with minsize as spacing

        # Button
        self.insertTool = customtkinter.CTkButton(master=self.frameTool,
                                                text="添加",
                                                command=self.insert_btn, 
                                                fg_color = "#d1d5d8",
                                                hover_color = "#BEBEBE")
        self.insertTool.grid(row=1, column=0, pady=(3,1), padx=5)
        self.insertTool.config(width = 70)

        self.removeTool = customtkinter.CTkButton(master=self.frameTool,
                                                text="全部移除",
                                                command=self.removeAll,
                                                fg_color = "#d1d5d8",
                                                hover_color = "#BEBEBE")
        self.removeTool.grid(row=2, column=0, pady=1, padx=5)
        self.removeTool.config(width = 70)
        
        # PROCESSING DATA
        

        # Adding menu
        menubar = Menu(self)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="新增", command=self.openNew)
        filemenu.add_command(label="開啟", command=self.open)
        filemenu.add_command(label="儲存", command=self.saveFile)
        filemenu.add_command(label="另存新檔", command=self.saveNew)
        filemenu.add_separator()
        filemenu.add_command(label="離開", command=self.quit)
        # Warning should be added ^ (save, exit, cancel)
        menubar.add_cascade(label="檔案", menu=filemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="查詢", command=self.donothing)
        helpmenu.add_command(label="關於...", command=self.donothing)
        menubar.add_cascade(label="說明", menu=helpmenu)

        self.config(menu = menubar)

        #item1 = Item("品項1", 1, "g", "243")
        #item2 = Item("品項2", 45, "teaspoon", "419")
        #item3 = Item("品項3", 3, "cup", "432")

        #self.insert_element(item1, 72)
        #self.insert_element(item2, 78)
        #self.insert_element(item3, 75)
    def donothing(self):
        pass

    def donothing2Arg(self, event):
        pass

    def on_closing(self, event=0):
        if not self.save:
            response = messagebox.askyesnocancel("Info", "是否要儲存此檔案")

            if response:
                dialogResponse = self.saveFile()
                if not dialogResponse:
                    return

            elif response == None:
                return
            
        self.destroy()

    def change_appearance_mode(self, new_appearance_mode):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def insert_btn(self):
        self.insertWindow = customtkinter.CTkToplevel(self)
        self.insertWindow.title("新增項目")
        self.insertWindow.geometry("700x200")
        self.insertWindow.iconbitmap(os.path.join(PATH, "icon.ico"))
        
        # Frame setup
        #self.insertWindow.grid_columnconfigure(0, weight=1)
        #self.insertWindow.grid_rowconfigure(0, weight=1)
        #self.insertWindow.frame = customtkinter.CTkFrame(master = self.insertWindow, width = 650, corner_radius=0)
        #self.insertWindow.frame.grid(row = 0, column = 0, sticky = "nswe", rowspan = 2)
        self.insertWindow.grab_set()

        

        #Label
        self.label_1 = customtkinter.CTkLabel(master=self.insertWindow,
                                              text="樣品",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        self.label_1.grid(row=0, column=0, pady=10, padx=10)

        self.label_2 = customtkinter.CTkLabel(master=self.insertWindow,
                                              text="量",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        self.label_2.grid(row=0, column=1, pady=10, padx=10)

        self.label_3 = customtkinter.CTkLabel(master=self.insertWindow,
                                              text="單位",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        self.label_3.grid(row=0, column=2, pady=10, padx=10)
        
        self.label_4 = customtkinter.CTkLabel(master=self.insertWindow,
                                              text="每一百公克卡路里含量",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        self.label_4.grid(row=0, column=3, pady=10, padx=10)

        conn = sqlite3.connect(os.path.join(PATH, "saved_items"))
        c = conn.cursor()
        c.execute("SELECT * FROM items")
        temp = c.fetchall()
        items = [x[0] for x in temp]
        conn.close() 

        itemcombo = ttk.Combobox(master = self.insertWindow, values = items, state = "readonly")
        itemcombo.grid(row = 1, column = 0, padx = 5, pady = (1,5), sticky = "nswe")

        # Cal per 100 gram
        self.p100gEntry = customtkinter.CTkEntry(master = self.insertWindow, placeholder_text = "")
        self.p100gEntry.grid(row=1,column=3, padx = 2, pady = (1,5), sticky = "nswe")

        # Updates entry box
        def updateEntry(event):
            self.entry.delete(0,"end")
            self.entry.insert(0, event.widget.get())

            # Connecting to database
            conn = sqlite3.connect(os.path.join(PATH, "saved_items"))
            c = conn.cursor()

            self.p100gEntry.delete(0, "end")
            c.execute("SELECT cal FROM items WHERE name = (?)", (event.widget.get(),))
            self.p100gEntry.insert(0, c.fetchone())
            conn.close()  
        itemcombo.bind("<<ComboboxSelected>>",updateEntry)


        # Updating options based on search
        def update(event):
            a = event.widget.get().lower()
            newVal = [i for i in items if a in i]
            itemcombo["values"] = newVal

        # Entry overlaying Combobox
        self.entry = Entry(self.insertWindow, width = 18, borderwidth = 0, highlightthickness=0, font = "normal 10")
        self.entry.place(height = 10)
        self.entry.bind('<KeyRelease>', update)
        self.entry.grid(row = 1, column = 0, padx = (7,5), ipady = 8.4, ipadx = 2, sticky = "w")


        # Quantity and Unit
        quantityEntry = customtkinter.CTkEntry(master = self.insertWindow, placeholder_text = "")
        quantityEntry.grid(row=1,column=1, padx = 2, pady = (1,5), sticky = "nswe")
        quantityEntry.config(justify = 'right', width = 20)

        units = ["mg","g","kg","liang","jin","lb","oz"]
        unitoption = customtkinter.CTkOptionMenu(master = self.insertWindow, values = units, fg_color = "white", command = self.donothing2Arg)
        unitoption.grid(row = 1, column = 2, padx = 2, pady = (1,5), sticky = "nswe")
        unitoption.set("g")
        unitoption.config(width = 5)

        # Buttons        
        insertExit = customtkinter.CTkButton(master=self.insertWindow,
                                                text="取消",
                                                command=self.insertWindow.destroy)
        
        insertExit.grid(row=2, column=1, pady=3, padx=5)
        insertExit.config(width = 100)

        insertInsert = customtkinter.CTkButton(master=self.insertWindow,
                                                text="新增",
                                                command=lambda: self.insert_element(self.entry.get(),
                                                                                    quantityEntry.get(),
                                                                                    unitoption.get(),
                                                                                    self.p100gEntry.get()))
        
        insertInsert.grid(row=2, column=0, pady=3, padx=5)
        insertInsert.config(width = 100)
        
        insertSearch = customtkinter.CTkButton(master=self.insertWindow,
                                                text="搜尋...",
                                                command=lambda: self.search(self.entry.get()))
        
        insertSearch.grid(row=2, column=2, pady=3, padx=5)
        insertSearch.config(width = 100)

        def deleteFromDb():
            # Connecting to database
            conn = sqlite3.connect(os.path.join(PATH, "saved_items"))
            c = conn.cursor()
            c.execute("DELETE FROM items WHERE name = (?)", (self.entry.get(),))
            conn.commit()
            conn.close()
        insertDelete = customtkinter.CTkButton(master=self.insertWindow,
                                                text="從記錄刪除",
                                                command=deleteFromDb)

        self.insertWindow.update()
        
        insertDelete.grid(row=3, column=0, pady=3, padx=5)
        insertDelete.config(width = 100)

        def deleteAll():
            response = messagebox.askyesno("Warning", "確認是否全部移除?")
            if response == False:
                return
            # Connecting to database
            conn = sqlite3.connect(os.path.join(PATH, "saved_items"))
            c = conn.cursor()
            c.execute("DELETE FROM items")
            conn.commit()
            conn.close()

        insertDeleteAll = customtkinter.CTkButton(master=self.insertWindow,
                                                text="刪除紀錄",
                                                fg_color = "red",
                                                text_color = "#edebeb",
                                                hover_color = "#870000",
                                                command=deleteAll)
        
        insertDeleteAll.grid(row=3, column=1, pady=3, padx=5)
        insertDeleteAll.config(width = 100)

    def search(self, name):
        pass
        
    # Window for editing value   
    def edit(self, event):
        # Selected item values to set as default value for edit screen
        try:
            curName = self.itemTree.item(self.itemTree.focus())["values"][0]
            curQuantity = self.itemTree.item(self.itemTree.focus())["values"][1]
            curUnit = self.itemTree.item(self.itemTree.focus())["values"][2]
            curp100g = self.itemTree.item(self.itemTree.focus())["values"][3]
        # Double clicked on nothing
        except IndexError:
            return

        index = int(self.itemTree.selection()[0])
        
        # Creating Window
        self.editWindow = customtkinter.CTkToplevel(self)
        self.editWindow.title("編輯")
        self.editWindow.geometry("450x120")
        self.editWindow.iconbitmap(os.path.join(PATH, "icon.ico"))
        self.editWindow.grab_set()

        #Labels for Edit Window
        self.label_quantity = customtkinter.CTkLabel(master=self.editWindow,
                                              text="量",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        self.label_quantity.grid(row=0, column=0, pady=10, padx=2)

        self.label_p100g = customtkinter.CTkLabel(master=self.editWindow,
                                              text="每100g卡路里",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        self.label_p100g.grid(row=0, column=2, pady=10, padx=2)

        self.label_unit = customtkinter.CTkLabel(master=self.editWindow,
                                              text="單位",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        self.label_unit.grid(row=0, column=1, pady=10, padx=2)

        # Entries
        # Cal per 100 gram
        self.p100gEntry = customtkinter.CTkEntry(master = self.editWindow, placeholder_text = "")
        self.p100gEntry.insert(0, curp100g)
        self.p100gEntry.grid(row=1,column=2, padx = 2, pady = (1,5), sticky = "nswe")

        # Quantity and Unit
        quantityEntry = customtkinter.CTkEntry(master = self.editWindow, placeholder_text = "")
        quantityEntry.grid(row=1,column=0, padx = 2, pady = (1,5), sticky = "nswe")
        quantityEntry.insert(0, curQuantity)
        quantityEntry.config(justify = 'right', width = 20)

        units = ["mg","g","kg","liang","jin","lb","oz"]
        unitoption = customtkinter.CTkOptionMenu(master = self.editWindow, values = units, fg_color = "white", command = self.donothing2Arg)
        unitoption.grid(row = 1, column = 1, padx = 2, pady = (1,5), sticky = "nswe")
        unitoption.set(curUnit)
        unitoption.config(width = 5)

        # Buttons for Edit Window
        editEnter = customtkinter.CTkButton(master=self.editWindow,
                                                text="確認",
                                                command=lambda: self.editEnter(curName, index, quantityEntry.get(), unitoption.get(), self.p100gEntry.get()))
        
        editEnter.grid(row=2, column=0, pady=3, padx=5)
        editEnter.config(width = 100)

        editExit = customtkinter.CTkButton(master=self.editWindow,
                                                text="取消",
                                                command=self.editWindow.destroy)
        
        editExit.grid(row=2, column=1, pady=3, padx=5)
        editExit.config(width = 100)


    def editEnter(self, name, index, quantity, unit, p100g):
        # Check info
        if len(quantity) == 0 or len(p100g) == 0:
            responseFill = messagebox.showinfo("Info", "請完整填寫")
            return

        if quantity.isdigit() and p100g.isdigit():
            pass
        elif quantity.replace(".", "1").isdigit() and quantity.count(".")<2 and p100g.replace(".", "1").isdigit() and p100g.count(".")<2 and not p100g[-1] == "." and not quantity[-1] == ".":
            pass
        else:
            responseNum = messagebox.showinfo("Info", "第一與三欄只接受數字")
            return
        pass

        self.itemList[index].quantity = quantity
        self.itemList[index].unit = unit
        self.itemList[index].p100g = p100g

        for i in self.itemTree.get_children():
            self.itemTree.delete(i)

        for item in self.itemList:
            self.itemTree.insert(parent = "", 
                                index = "end", 
                                iid = self.itemList.index(item), 
                                values = (item.name, item.quantity, 
                                item.unit, 
                                item.p100g))
        # Connecting to database
        conn = sqlite3.connect(os.path.join(PATH, "saved_items"))
        c = conn.cursor()
        c.execute('SELECT name FROM items WHERE name = (?)', (name,))
        try:
            result = c.fetchone()[0]
            c.execute('UPDATE items SET cal = (?) WHERE name = (?)', (p100g,name))
            conn.commit()
        except TypeError:
            c.execute("INSERT INTO items VALUES(?,?)", (name, p100g))
            conn.commit()

        conn.close()

        # Update Data
        self.currP100G.set(f"Kcal/100g: {self.kcalP100G(self.itemList)}")
        self.currKcal.set(f"總卡路里: {self.totalKCal(self.itemList)}")

        if self.save:
            self.save = False
            if self.currDir == "":
                self.title(f"• 未儲存 - Calorie")
            else:
                self.title(f"• {os.path.basename(self.currDir)} - Calorie")

        
        self.editWindow.destroy()

    def insert_element(self, name, quantity, unit, p100g):
        # Check info
        if len(name) == 0 or len(quantity) == 0 or len(p100g) == 0:
            responseFill = messagebox.showinfo("Info", "請完整填寫")
            return

        if quantity.isdigit() and p100g.isdigit():
            pass
        elif quantity.replace(".", "1").isdigit() and quantity.count(".")<2 and p100g.replace(".", "1").isdigit() and p100g.count(".")<2 and not p100g[-1] == "." and not quantity[-1] == ".":
            pass
        else:
            responseNum = messagebox.showinfo("Info", "第二與四欄只接受數字")
            return

        self.itemList.append(Item(name, quantity, unit, p100g))
        for i in self.itemTree.get_children():
            self.itemTree.delete(i)

        for item in self.itemList:
            self.itemTree.insert(parent = "", 
                                index = "end", 
                                iid = self.itemList.index(item), 
                                values = (item.name, item.quantity, 
                                item.unit, 
                                item.p100g))

        if self.save:
            self.save = False
            if self.currDir == "":
                self.title(f"• 未儲存 - Calorie")
            else:
                self.title(f"• {os.path.basename(self.currDir)} - Calorie")

        # Connecting to database
        conn = sqlite3.connect(os.path.join(PATH, "saved_items"))
        c = conn.cursor()
        c.execute('SELECT name FROM items WHERE name = (?)', (name,))
        try:
            result = c.fetchone()[0]
            c.execute('UPDATE items SET cal = (?) WHERE name = (?)', (p100g,name))
            conn.commit()
        except TypeError:
            c.execute("INSERT INTO items VALUES(?,?)", (name, p100g))
            conn.commit()

        self.currP100G.set(f"Kcal/100g: {self.kcalP100G(self.itemList)}")
        self.currKcal.set(f"總卡路里: {self.totalKCal(self.itemList)}")
        conn.close()
        #self.itemTree.insert(parent = "", index = "end", iid = id, values = (item.name, item.quantity, item.unit, item.p100g))

    # Searches data from database
    def search(self, name):
        if name == None:
            name = ""
        # Creating Window
        self.searchWindow = customtkinter.CTkToplevel(self)
        self.searchWindow.title("搜尋...")
        self.searchWindow.iconbitmap(os.path.join(PATH, "icon.ico"))
        self.searchWindow.geometry("800x120")

        self.searchWindow.grid_columnconfigure(0, weight=1)
        self.searchWindow.grid_rowconfigure(0, weight=1)
        
        self.searchWindow.attributes("-topmost", "true")

        self.searchWindow.grab_set()

        # Create Treeview
        self.searchResults = []
        self.searchTree = ttk.Treeview(self.searchWindow, selectmode = "browse")
        self.searchTree["columns"] = ["item", "kcal", "note", "source"]
        ttk.Style().configure('Treeview', rowheight = 26)

        # formatting column
        self.searchTree.column("#0", width = 0, stretch = NO)
        self.searchTree.column("item", anchor = W, width = 120)
        self.searchTree.column("kcal", anchor = E, width = 70)
        self.searchTree.column("note", anchor = E, width = 70)
        self.searchTree.column("source", anchor = E, width = 70)

        # Treeview headings
        self.searchTree.heading("#0", text = "", anchor = W)
        self.searchTree.heading("item", text = "樣品名稱", anchor = W)
        self.searchTree.heading("kcal", text = "卡路里", anchor = E)
        self.searchTree.heading("note", text = "備註", anchor = E)
        self.searchTree.heading("source", text = "資料來源", anchor = E)

        self.searchTree.grid(row = 0, column = 0, sticky = "nswe", padx = 10, pady = (10,5))

        # Put selection into insert
        def updateInsertEntries(event):
            curName = self.searchTree.item(self.searchTree.focus())["values"][0]
            curKcal = self.searchTree.item(self.searchTree.focus())["values"][1]

            self.entry.delete(0,"end")
            self.entry.insert(0, curName)

            self.p100gEntry.delete(0, "end")
            self.p100gEntry.insert(0, curKcal)

            self.searchWindow.destroy()

        self.searchTree.bind("<Double-Button-1>", updateInsertEntries)
        #self.searchTree.bind("<Double-Button-1>", self.edit)
        #self.searchTree.bind("<Delete>", self.removeElement)

        # Creating right frame
        self.searchFrame = customtkinter.CTkFrame(master = self.searchWindow, corner_radius=10, width = 125)
        self.searchFrame.grid(row = 0, column = 1, sticky = "nswe", padx = 5, pady = 5)

        # Creating Label
        #Labels for Edit Window
        label_checkbox = customtkinter.CTkLabel(master=self.searchFrame,
                                              text="資料庫勾選",
                                              text_font=("Roboto Medium", -14))  # font name and size in px
        label_checkbox.grid(row=0, column=0, pady=(5,1), padx=2)

        def updateSearch():
            pass
        
        def searchFDA(name):
            if len(name) == 0:
                return []
            # Creates Search Results
            trans = Translator()
            name = trans.translate(name, dest = "zh-tw").text

            conn = sqlite3.connect(os.path.join(PATH, "item_data"))
            c = conn.cursor()

            name = "%" + name + "%"

            c.execute("SELECT * FROM items_FDA WHERE com LIKE (?) OR name LIKE (?)", (name,name,))
            
            temp = c.fetchall()
            #for i in temp:
            #    self.searchResults.append(searchItem(i[0],i[1],i[4],"衛福部食品藥物管理署"))

            conn.close()
            return temp

        def searchFDC(name):
            if len(name) == 0:
                return []
            # Tries to translate language
            temp = []
            trans = Translator()
            name = trans.translate(name).text

            # REMEMBER TO HIDE THIS IN THE END
            api_key = "jV7JnR8PB9Yae0W8dZoalu6ArtRqQohaABDcrZaa"
            trans = Translator()
            name = trans.translate(name).text

            x = requests.get(f"https://api.nal.usda.gov/fdc/v1/foods/search?&query={name}&dataType=Survey (FNDDS)&pageSize=15&api_key={api_key}")
            x = x.json()
            for i in x["foods"]:
                if not name.lower() in i["description"].lower():
                    continue
                #print(type(i["foodNutrients"]))
                #print(i["foodNutrients"])
                #print("~~~~~~~~~")
                #print("~~~~~~~~~")
                for nutrient in i["foodNutrients"]:
                    if nutrient["nutrientName"] == "Energy":
                        temp.append((i["description"], nutrient["value"], ""))

            # Find branded if no survey
            if len(temp) == 0:
                x = requests.get(f"https://api.nal.usda.gov/fdc/v1/foods/search?&query={name}&dataType=Branded&dataType=description&dataType=description&pageSize=5&api_key={api_key}")
                x = x.json()
                for i in x["foods"]:
                    #print(type(i["foodNutrients"]))
                    #print(i["foodNutrients"])
                    #print("~~~~~~~~~")
                    #print("~~~~~~~~~")
                    for nutrient in i["foodNutrients"]:
                        if nutrient["nutrientName"] == "Energy":
                            try:
                                temp.append((i["description"], nutrient["value"], i["brandName"]))
                            except KeyError:
                                try:
                                    temp.append((i["description"], nutrient["value"], i["brandOwner"]))
                                except KeyError:
                                    temp.append((i["description"], nutrient["value"], ""))

            return temp


        # Creating Checkboxes for source
        self.FDACheckVar = IntVar(value = 1)
        self.FDACheck = customtkinter.CTkCheckBox(master = self.searchFrame, text = "衛福部食品藥物管理署", variable = self.FDACheckVar, command = self.FDAEvent)
        self.FDACheck.grid(row = 1, column = 0, pady=1, sticky = "nswe", padx=10)
        
        self.FDCCheckVar = IntVar(value = 1)
        self.FDCCheck = customtkinter.CTkCheckBox(master = self.searchFrame, text = "美國農業部(USDA)", variable = self.FDCCheckVar, command = self.FDCEvent)
        self.FDCCheck.grid(row = 2, column = 0, pady=1, sticky = "nswe", padx=10)
        
        self.fda_list = searchFDA(name)
        self.fdc_list = searchFDC(name)

        # Detect language to put into priority
        trans = Translator()

        if not len(name) == 0 and (trans.detect(name).lang == "zh-CN" or trans.detect(name).lang == "zh-TW"):
            # Adding fda results
            for i in self.fda_list:
                self.searchResults.append(searchItem(i[0],i[1],i[4],"衛福部食品藥物管理署"))
            # Adding fdc results
            for i in self.fdc_list:
                self.searchResults.append(searchItem(i[0],i[1],i[2],"美國農業部(USDA)"))
        elif not len(name) == 0:
            # Adding fdc results
            for i in self.fdc_list:
                self.searchResults.append(searchItem(i[0],i[1],i[2],"美國農業部(USDA)"))
             # Adding fda results
            for i in self.fda_list:
                self.searchResults.append(searchItem(i[0],i[1],i[4],"衛福部食品藥物管理署"))

        for i in self.searchTree.get_children():
            self.searchTree.delete(i)

        for item in self.searchResults:
            self.searchTree.insert(parent = "", 
                                index = "end", 
                                iid = self.searchResults.index(item), 
                                values = (item.name, item.kcal, 
                                item.note, 
                                item.source))

    def removeElement(self, event):
        # Remove item from list
        index = int(self.itemTree.selection()[0])
        self.itemList.pop(index)

        # Update treeview
        for i in self.itemTree.get_children():
            self.itemTree.delete(i)

        for item in self.itemList:
            self.itemTree.insert(parent = "", 
                                index = "end", 
                                iid = self.itemList.index(item), 
                                values = (item.name, item.quantity, 
                                item.unit, 
                                item.p100g))

        self.currP100G.set(f"Kcal/100g: {self.kcalP100G(self.itemList)}")
        self.currKcal.set(f"總卡路里: {self.totalKCal(self.itemList)}")

    def FDAEvent(self):
        if self.FDACheckVar.get() == 0:
            for i in self.searchResults:
                if i.source == "衛福部食品藥物管理署":
                    return

            for i in self.fda_list:
                self.searchResults.append(searchItem(i[0],i[1],i[4],"衛福部食品藥物管理署"))

            for i in self.searchTree.get_children():
                self.searchTree.delete(i)

            for item in self.searchResults:
                self.searchTree.insert(parent = "", 
                                    index = "end", 
                                    iid = self.searchResults.index(item), 
                                    values = (item.name, item.kcal, 
                                    item.note, 
                                    item.source))
        else:
            temp = copy.deepcopy(self.searchResults)
            for i in temp:
                if i.source == "衛福部食品藥物管理署":
                    self.searchResults.remove(i)

            for i in self.searchTree.get_children():
                self.searchTree.delete(i)

            for item in self.searchResults:
                self.searchTree.insert(parent = "", 
                                    index = "end", 
                                    iid = self.searchResults.index(item), 
                                    values = (item.name, item.kcal, 
                                    item.note, 
                                    item.source))

    def FDCEvent(self):
        if self.FDCCheckVar.get() == 0:
            for i in self.searchResults:
                if i.source == "美國農業部(USDA)":
                    return

            for i in self.fdc_list:
                self.searchResults.append(searchItem(i[0],i[1],i[2],"美國農業部(USDA)"))

            for i in self.searchTree.get_children():
                self.searchTree.delete(i)

            for item in self.searchResults:
                self.searchTree.insert(parent = "", 
                                    index = "end", 
                                    iid = self.searchResults.index(item), 
                                    values = (item.name, item.kcal, 
                                    item.note, 
                                    item.source))
        else:
            temp = copy.deepcopy(self.searchResults)
            for i in temp:
                if i.source == "美國農業部(USDA)":
                    self.searchResults.remove(i)

            for i in self.searchTree.get_children():
                self.searchTree.delete(i)

            for item in self.searchResults:
                self.searchTree.insert(parent = "", 
                                    index = "end", 
                                    iid = self.searchResults.index(item), 
                                    values = (item.name, item.kcal, 
                                    item.note, 
                                    item.source))

    # Converts other units to grams
    def gramConversion(self, quantity, unit):
        #units = ["毫克","克","公斤","兩","斤","磅","盎司"]
        f_quantity = float(quantity)
        conversion = [0.001, 1, 1000, 37.5, 600, 28.3495]
        
        return round(f_quantity*conversion[unit], 2)

    def removeAll(self):
        response = messagebox.askyesno("Warning", "確認是否全部移除?")
        if response == False:
            return
        for i in self.itemTree.get_children():
            self.itemTree.delete(i)

        self.currP100G.set(f"Kcal/100g: {self.kcalP100G(self.itemList)}")
        self.currKcal.set(f"總卡路里: {self.totalKCal(self.itemList)}")

    # Calculates Kcal per 100 gram
    def kcalP100G(self, items):
        totalKCal = 0
        totalGram = 0

        for i in items:
            totalKCal += float(i.quantityGram)/100.0*float(i.p100g)
            totalGram += float(i.quantityGram)

        try:
            kCalP100G = totalKCal * 100.0 / totalGram
        except ZeroDivisionError:
            return 0
        return f"{kCalP100G:g}"

    #Calculates total Kcal
    def totalKCal(self, items):
        totalKCal = 0
    
        for i in items:
            totalKCal += round(float(i.quantityGram),2)/100.0*round(float(i.p100g),2)

        return f'{totalKCal:g}'
        #return round(totalKCal, 2)

    def calculateKcal(self, designated, items):
        kCalP100G = self.kcalP100G(items)
        return f'{(float(designated)/100 * float(kCalP100G)):g}'
        #return round(float(designated)/100.0 * kCalP100G, 2)

    # Opens a new file
    def openNew(self):
        if self.save == False:
            response = messagebox.askyesno("Warning", "是否要儲存本檔案")
            if response == True:
                dialogResponse = self.saveFile()
                if not dialogResponse:
                    return

        self.itemList = []

        for i in self.itemTree.get_children():
            self.itemTree.delete(i)

        self.currDir = ""
        self.save = True
        self.title("未儲存 - Calorie")

    # Opens a file
    def open(self):
        if self.save == False:
            response = messagebox.askyesno("Warning", "是否要儲存本檔案")
            if response == True:
                dialogResponse = self.saveFile()
                if not dialogResponse:
                    return
        
        file = filedialog.askopenfile(title = "開啟", filetypes = [("JSON Files", "*.json")])

        # In case close the file dialog
        try:
            data = json.load(file)
        except AttributeError:
            return
        
        # in case the file does not load
        backupList = copy.deepcopy(self.itemList)
        
        self.itemList = []
        try:
            for i in data:
                self.itemList.append(Item(i['name'], i['quantity'], i['unit'], i['p100g']))

            for i in self.itemTree.get_children():
                self.itemTree.delete(i)

            for item in self.itemList:
                self.itemTree.insert(parent = "", 
                                    index = "end", 
                                    iid = self.itemList.index(item), 
                                    values = (item.name, item.quantity, 
                                    item.unit, 
                                    item.p100g))
        except KeyError:
            self.itemList = backupList
            response = messagebox.showerror("Error", "檔案格式錯誤或不支援")
            return

        self.currDir = file.name
        self.save = True

        self.title(f"{os.path.basename(self.currDir)} - Calorie")


    def saveFile(self, v = None):
        if self.currDir == "":
            self.saveNew()
            return

        data = []
        for i in self.itemList:
            data.append({"name": i.name, "quantity": i.quantity, "unit": i.unit, "p100g": i.p100g})
        
        with open(self.currDir,"w") as f:
            json.dump(data, f)

        self.title(f"{os.path.basename(self.currDir)} - Calorie")
        self.save = True

    def saveNew(self):
        data = []
        for i in self.itemList:
            data.append({"name": i.name, "quantity": i.quantity, "unit": i.unit, "p100g": i.p100g})
        fileSave = filedialog.asksaveasfilename(defaultextension = ".html", initialdir = "DocumentFolder", title = "另存新檔", filetypes = [("JSON files", "*.json")], initialfile = "未命名")

        try:
            with open(fileSave, "w") as f:
                json.dump(data, f)
        except FileNotFoundError:
            return False

        self.title(f"{os.path.basename(fileSave)} - Calorie")
        self.save = True
        self.currDir = fileSave

if __name__ == "__main__":
    app = App()
    app.mainloop()
