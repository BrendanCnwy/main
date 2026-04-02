import calendar, datetime, tkinter as tk  # Import necessary modules for calendar, dates, and GUI
from tkinter import ttk, messagebox  # Import themed widgets and message boxes

class CalendarApp(tk.Tk):  # Main calendar application class inheriting from Tk
    def __init__(self):
        super().__init__()
        self.title("Graphical Calendar"); self.geometry("1000x640"); self.minsize(900,600); self.configure(bg="#111")  # Set window title, size, min size, and background
        s=ttk.Style(self); s.theme_use("clam")  # Initialize style and set theme
        s.configure("D.TFrame",background="#111"); s.configure("D.TLabelframe",background="#191919",foreground="white")  # Configure dark frame and labelframe styles
        s.configure("D.TLabelframe.Label",background="#191919",foreground="white",font=(None,12,"bold"))  # Configure labelframe label style
        s.configure("D.TLabel",background="#111",foreground="white"); s.configure("D.TButton",background="#333",foreground="white",borderwidth=0)  # Configure label and button styles
        s.map("D.TButton",background=[("active","#444"),("pressed","#555")]); s.configure("D.TEntry",fieldbackground="#222",foreground="white",background="#222")  # Map button states and configure entry style
        self.today=datetime.date.today(); self.current_year=self.today.year; self.current_month=self.today.month; self.selected_date=self.today  # Initialize date variables
        self.events={}; self.alarms={}  # Initialize event and alarm dictionaries
        self.columnconfigure(0,weight=1); self.rowconfigure(0,weight=1)  # Configure main window grid
        self._build_ui(); self._update_calendar(); self._update_event_display(); self.after(1000,self._check_alarms)  # Build UI, update displays, start alarm checking

    def _build_ui(self):  # Build the main user interface
        f=ttk.Frame(self,padding=10,style="D.TFrame"); f.grid(row=0,column=0,sticky="nsew")  # Create main frame
        f.columnconfigure(0,weight=3); f.columnconfigure(1,weight=1); f.rowconfigure(0,weight=1)  # Configure main frame grid
        cp=ttk.Frame(f,style="D.TFrame"); cp.grid(row=0,column=0,sticky="nsew",padx=(0,10)); cp.columnconfigure(0,weight=1); cp.rowconfigure(2,weight=1)  # Create calendar panel
        self._build_header(cp); self._build_weekdays(cp); self._build_calendar(cp); self._build_event_panel(f)  # Build sub-components

    def _build_header(self,p):  # Build the header with month/year and navigation buttons
        h=ttk.Frame(p,padding=(0,0,0,10),style="D.TFrame"); h.grid(row=0,column=0,sticky="ew")  # Create header frame
        ttk.Button(h,text="⟵",width=4,style="D.TButton",command=self._show_prev_month).grid(row=0,column=0,padx=(0,8))  # Previous month button
        self.month_label=ttk.Label(h,text="",style="D.TLabel"); self.month_label.grid(row=0,column=1,padx=8)  # Month label
        self.year_label=ttk.Label(h,text="",style="D.TLabel"); self.year_label.grid(row=0,column=2,padx=8)  # Year label
        ttk.Button(h,text="⟶",width=4,style="D.TButton",command=self._show_next_month).grid(row=0,column=3,padx=(8,0))  # Next month button

    def _build_weekdays(self,p):  # Build the weekday labels
        d=ttk.Frame(p,padding=(0,0,0,5),style="D.TFrame"); d.grid(row=1,column=0,sticky="ew")  # Create weekdays frame
        for i,day in enumerate(calendar.day_abbr): ttk.Label(d,text=day,width=10,anchor="center",style="D.TLabel").grid(row=0,column=i,padx=2,pady=2)  # Add weekday labels

    def _build_calendar(self,p):  # Build the calendar grid of buttons
        self.days_frame=ttk.Frame(p,padding=5,style="D.TFrame"); self.days_frame.grid(row=2,column=0,sticky="nsew")  # Create calendar frame
        for i in range(7): self.days_frame.columnconfigure(i,weight=1)  # Configure columns
        self.day_buttons=[]  # Initialize button list
        for r in range(6):  # For each week row
            row=[]  # Initialize row list
            for c in range(7):  # For each day column
                btn=tk.Button(self.days_frame,text="",width=10,height=4,relief="flat",bg="#1f1f1f",fg="white",activebackground="#333",activeforeground="white",disabledforeground="#555",bd=0,highlightthickness=1,highlightbackground="#222",command=lambda rr=r,cc=c: self._select_day(rr,cc))  # Create day button
                btn.grid(row=r,column=c,padx=3,pady=3,sticky="nsew"); row.append(btn)  # Grid and append button
            self.day_buttons.append(row)  # Append row to buttons

    def _build_event_panel(self,p):  # Build the event and alarm panel
        ep=ttk.LabelFrame(p,text="Day Events",padding=12,style="D.TLabelframe"); ep.grid(row=0,column=1,sticky="nsew")  # Create event panel
        ep.columnconfigure(0,weight=1); ep.rowconfigure(2,weight=1); ep.rowconfigure(6,weight=1)  # Configure panel grid
        self.selected_label=ttk.Label(ep,text="Selected: ",style="D.TLabel"); self.selected_label.grid(row=0,column=0,sticky="w")  # Selected date label
        ttk.Label(ep,text="Events",style="D.TLabel").grid(row=1,column=0,sticky="w",pady=(8,0))  # Events section label
        self.event_listbox=tk.Listbox(ep,font=(None,11),activestyle="none",bg="#1b1b1b",fg="white",selectbackground="#4a4aff",selectforeground="white",highlightthickness=1,highlightbackground="#333333",borderwidth=0)  # Create event listbox
        self.event_listbox.grid(row=2,column=0,sticky="nsew",pady=(4,8))  # Grid event listbox
        ef=ttk.Frame(ep,style="D.TFrame"); ef.grid(row=3,column=0,sticky="ew",pady=(0,8)); ef.columnconfigure(0,weight=1)  # Create event entry frame
        self.event_entry=ttk.Entry(ef,style="D.TEntry"); self.event_entry.grid(row=0,column=0,sticky="ew")  # Event entry field
        ttk.Button(ef,text="Add Event",style="D.TButton",command=self._add_event).grid(row=0,column=1,padx=(8,0))  # Add event button
        ttk.Button(ep,text="Remove Selected Event",style="D.TButton",command=self._remove_event).grid(row=4,column=0,sticky="ew",pady=(0,12))  # Remove event button
        ttk.Label(ep,text="Alarms (24h)",style="D.TLabel").grid(row=5,column=0,sticky="w")  # Alarms section label
        self.alarm_listbox=tk.Listbox(ep,font=(None,11),activestyle="none",bg="#1b1b1b",fg="white",selectbackground="#4a4aff",selectforeground="white",highlightthickness=1,highlightbackground="#333333",borderwidth=0)  # Create alarm listbox
        self.alarm_listbox.grid(row=6,column=0,sticky="nsew",pady=(4,8))  # Grid alarm listbox
        af=ttk.Frame(ep,style="D.TFrame"); af.grid(row=7,column=0,sticky="ew",pady=(0,8)); af.columnconfigure(1,weight=1)  # Create alarm entry frame
        self.alarm_time_entry=ttk.Entry(af,width=8,style="D.TEntry"); self.alarm_time_entry.grid(row=0,column=0,padx=(0,8))  # Alarm time entry
        self.alarm_text_entry=ttk.Entry(af,style="D.TEntry"); self.alarm_text_entry.grid(row=0,column=1,sticky="ew",padx=(0,8))  # Alarm text entry
        ttk.Button(af,text="Add Alarm",style="D.TButton",command=self._add_alarm).grid(row=0,column=2)  # Add alarm button
        ttk.Label(ep,text="Enter a 24-hour time like 14:30 and a message.",style="D.TLabel").grid(row=8,column=0,sticky="w")  # Instruction label
        ttk.Button(ep,text="Remove Selected Alarm",style="D.TButton",command=self._remove_alarm).grid(row=9,column=0,sticky="ew",pady=(8,0))  # Remove alarm button

    def _update_calendar(self):  # Update the calendar display for the current month
        self.month_label.config(text=calendar.month_name[self.current_month]); self.year_label.config(text=str(self.current_year))  # Update month and year labels
        mc=calendar.monthcalendar(self.current_year,self.current_month)  # Get month calendar
        for r in range(6):  # For each row
            for c in range(7):  # For each column
                num=mc[r][c] if r<len(mc) else 0; btn=self.day_buttons[r][c]  # Get day number and button
                if not num: btn.config(text="",state="disabled",bg="#111")  # Disable empty days
                else:  # For valid days
                    d=datetime.date(self.current_year,self.current_month,num); sel=d==self.selected_date; today=d==self.today  # Check if selected or today
                    btn.config(text=str(num),state="normal",fg="white",bg="#4a4aff" if sel else "#3d5a8f" if today else "#1f1f1f")  # Configure button
        if self.selected_date.month!=self.current_month or self.selected_date.year!=self.current_year: self.selected_date=datetime.date(self.current_year,self.current_month,1)  # Reset selected date if needed
        self._update_event_display()  # Update event display

    def _update_event_display(self):  # Update the event and alarm lists for the selected date
        self.selected_label.config(text=f"Selected: {self.selected_date.strftime('%A, %B %d, %Y')}")  # Update selected date label
        k=self.selected_date.isoformat(); ev=self.events.get(k,[]); al=self.alarms.get(k,[])  # Get events and alarms for date
        self.event_listbox.delete(0,tk.END)  # Clear event listbox
        if ev: [self.event_listbox.insert(tk.END,e) for e in ev]  # Insert events
        else: self.event_listbox.insert(tk.END,"No events for this day")  # No events message
        self.alarm_listbox.delete(0,tk.END)  # Clear alarm listbox
        if al:  # If alarms exist
            for a in sorted(al,key=lambda x:x["time"]): self.alarm_listbox.insert(tk.END,f"{a['time']} - {a['text']}")  # Insert sorted alarms
        else: self.alarm_listbox.insert(tk.END,"No alarms for this day")  # No alarms message

    def _select_day(self,r,c):  # Select a day when button is clicked
        mc=calendar.monthcalendar(self.current_year,self.current_month)  # Get current month calendar
        if r<len(mc) and mc[r][c]: self.selected_date=datetime.date(self.current_year,self.current_month,mc[r][c]); self._update_calendar(); self._update_event_display()  # Set selected date and update

    def _add_event(self):  # Add a new event for the selected date
        t=self.event_entry.get().strip()  # Get event text
        if t: k=self.selected_date.isoformat(); self.events.setdefault(k,[]).append(t); self.event_entry.delete(0,tk.END); self._update_event_display()  # Add event and update

    def _remove_event(self):  # Remove the selected event
        sel=self.event_listbox.curselection()  # Get selected index
        if sel:  # If something selected
            k=self.selected_date.isoformat(); ev=self.events.get(k,[])  # Get events
            if sel[0]<len(ev): ev.pop(sel[0]); self.events.pop(k,None) if not ev else None; self._update_event_display()  # Remove event and update

    def _add_alarm(self):  # Add a new alarm for the selected date
        t=self.alarm_time_entry.get().strip(); m=self.alarm_text_entry.get().strip()  # Get time and message
        if not t or not m: messagebox.showerror("Missing alarm","Please enter both time and message for the alarm."); return  # Error if missing
        try: parsed=datetime.datetime.strptime(t,"%H:%M").time()  # Parse time
        except ValueError: messagebox.showerror("Invalid time","Use the 24-hour format HH:MM, for example 14:30."); return  # Error if invalid
        k=self.selected_date.isoformat(); self.alarms.setdefault(k,[]).append({"time":parsed.strftime("%H:%M"),"text":m,"triggered":False})  # Add alarm
        self.alarm_time_entry.delete(0,tk.END); self.alarm_text_entry.delete(0,tk.END); self._update_event_display()  # Clear fields and update

    def _remove_alarm(self):  # Remove the selected alarm
        sel=self.alarm_listbox.curselection()  # Get selected index
        if sel:  # If something selected
            k=self.selected_date.isoformat(); al=self.alarms.get(k,[])  # Get alarms
            if sel[0]<len(al): al.pop(sel[0]); self.alarms.pop(k,None) if not al else None; self._update_event_display()  # Remove alarm and update

    def _check_alarms(self):  # Check for alarms that should trigger
        now=datetime.datetime.now(); k=now.date().isoformat(); al=self.alarms.get(k,[])  # Get current time and alarms
        for a in al:  # For each alarm
            if not a.get("triggered"):  # If not triggered
                try: at=datetime.datetime.strptime(a["time"],"%H:%M").time()  # Parse alarm time
                except ValueError: continue  # Skip invalid
                if now.time()>=at: messagebox.showinfo("Alarm",f"Alarm for {now.strftime('%A, %B %d, %Y')} at {a['time']}: {a['text']}"); a["triggered"]=True  # Trigger alarm
        self.after(1000,self._check_alarms)  # Schedule next check

    def _show_prev_month(self):  # Navigate to previous month
        if self.current_month==1: self.current_month=12; self.current_year-=1  # Wrap to December previous year
        else: self.current_month-=1  # Decrement month
        self.selected_date=datetime.date(self.current_year,self.current_month,1); self._update_calendar()  # Update selected date and calendar

    def _show_next_month(self):  # Navigate to next month
        if self.current_month==12: self.current_month=1; self.current_year+=1  # Wrap to January next year
        else: self.current_month+=1  # Increment month
        self.selected_date=datetime.date(self.current_year,self.current_month,1); self._update_calendar()  # Update selected date and calendar

if __name__=="__main__":  # Run the application if this is the main module
    CalendarApp().mainloop()  # Create and start the app

    # Build the month/year header and navigation buttons.
    def _build_header(self, parent):
        header_frame = ttk.Frame(parent, padding=(0, 0, 0, 10), style="Dark.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew")

        prev_btn = ttk.Button(header_frame, text="⟵", width=4, style="Dark.TButton", command=self._show_prev_month)
        prev_btn.grid(row=0, column=0, padx=(0, 8))

        self.month_label = ttk.Label(header_frame, text="", style="Dark.Heading.TLabel")
        self.month_label.grid(row=0, column=1, padx=8)

        self.year_label = ttk.Label(header_frame, text="", style="Dark.Heading.TLabel")
        self.year_label.grid(row=0, column=2, padx=8)

        next_btn = ttk.Button(header_frame, text="⟶", width=4, style="Dark.TButton", command=self._show_next_month)
        next_btn.grid(row=0, column=3, padx=(8, 0))

    # Build the weekday labels shown above the dates.
    def _build_weekdays(self, parent):
        days_frame = ttk.Frame(parent, padding=(0, 0, 0, 5), style="Dark.TFrame")
        days_frame.grid(row=1, column=0, sticky="ew")

        for index, day in enumerate(calendar.day_abbr):
            label = ttk.Label(days_frame, text=day, width=10, anchor="center", style="Dark.TLabel")
            label.grid(row=0, column=index, padx=2, pady=2)

    # Build the calendar grid using buttons for each day.
    def _build_calendar(self, parent):
        self.days_frame = ttk.Frame(parent, padding=5, style="Dark.TFrame")
        self.days_frame.grid(row=2, column=0, sticky="nsew")
        for column_index in range(7):
            self.days_frame.columnconfigure(column_index, weight=1)
        self.day_buttons = []

        for week in range(6):
            week_row = []
            for day in range(7):
                btn = tk.Button(
                    self.days_frame,
                    text="",
                    width=10,
                    height=4,
                    relief="flat",
                    bg="#1f1f1f",
                    fg="white",
                    activebackground="#333333",
                    activeforeground="white",
                    disabledforeground="#555555",
                    bd=0,
                    highlightthickness=1,
                    highlightbackground="#222222",
                    command=lambda rw=week, cl=day: self._select_day(rw, cl),
                )
                btn.grid(row=week, column=day, padx=3, pady=3, sticky="nsew")
                week_row.append(btn)
            self.day_buttons.append(week_row)

    # Build the panel where event details are shown and edited.
    def _build_event_panel(self, parent):
        event_panel = ttk.LabelFrame(parent, text="Day Events", padding=12, style="Dark.TLabelframe")
        event_panel.grid(row=0, column=1, sticky="nsew")
        event_panel.columnconfigure(0, weight=1)
        event_panel.rowconfigure(2, weight=1)
        event_panel.rowconfigure(6, weight=1)

        self.selected_label = ttk.Label(event_panel, text="Selected: ", style="Dark.Subtitle.TLabel")
        self.selected_label.grid(row=0, column=0, sticky="w")

        event_title = ttk.Label(event_panel, text="Events", style="Dark.Subtitle.TLabel")
        event_title.grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.event_listbox = tk.Listbox(event_panel,font=(None,11),activestyle="none",bg="#1b1b1b",fg="white",selectbackground="#4a4aff",selectforeground="white",highlightthickness=1,highlightbackground="#333333",borderwidth=0)
        self.event_listbox.grid(row=1,column=0,sticky="nsew",pady=(8,8))

        entry_frame = ttk.Frame(event_panel, style="Dark.TFrame")
        entry_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        entry_frame.columnconfigure(0, weight=1)

        self.event_entry = ttk.Entry(entry_frame, style="Dark.TEntry")
        self.event_entry.grid(row=0, column=0, sticky="ew")

        add_button = ttk.Button(entry_frame, text="Add Event", style="Dark.TButton", command=self._add_event)
        add_button.grid(row=0, column=1, padx=(8, 0))

        remove_button = ttk.Button(event_panel, text="Remove Selected Event", style="Dark.TButton", command=self._remove_event)
        remove_button.grid(row=4, column=0, sticky="ew", pady=(0, 12))

        alarm_title = ttk.Label(event_panel, text="Alarms (24h)", style="Dark.Subtitle.TLabel")
        alarm_title.grid(row=5, column=0, sticky="w")

        self.event_listbox = tk.Listbox(event_panel,font=(None,11),activestyle="none",bg="#1b1b1b",fg="white",selectbackground="#4a4aff",selectforeground="white",highlightthickness=1,highlightbackground="#333333",borderwidth=0)
        self.event_listbox.grid(row=1,column=0,sticky="nsew",pady=(8,8))

        alarm_frame = ttk.Frame(event_panel, style="Dark.TFrame")
        alarm_frame.grid(row=7, column=0, sticky="ew", pady=(0, 8))
        alarm_frame.columnconfigure(1, weight=1)

        self.alarm_time_entry = ttk.Entry(alarm_frame, width=8, style="Dark.TEntry")
        self.alarm_time_entry.grid(row=0, column=0, padx=(0, 8))

        self.alarm_text_entry = ttk.Entry(alarm_frame, style="Dark.TEntry")
        self.alarm_text_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        alarm_add_button = ttk.Button(alarm_frame, text="Add Alarm", style="Dark.TButton", command=self._add_alarm)
        alarm_add_button.grid(row=0, column=2)

        alarm_note = ttk.Label(event_panel, text="Enter a 24-hour time like 14:30 and a message.", style="Dark.TLabel")
        alarm_note.grid(row=8, column=0, sticky="w")

        remove_alarm_button = ttk.Button(event_panel, text="Remove Selected Alarm", style="Dark.TButton", command=self._remove_alarm)
        remove_alarm_button.grid(row=9, column=0, sticky="ew", pady=(8, 0))

    # Update the calendar buttons to show the correct month.
    def _update_calendar(self):
        self.month_label.config(text=calendar.month_name[self.current_month])
        self.year_label.config(text=str(self.current_year))

        month_calendar = calendar.monthcalendar(self.current_year, self.current_month)

        for week_index in range(6):
            for day_index in range(7):
                day_number = month_calendar[week_index][day_index] if week_index < len(month_calendar) else 0
                button = self.day_buttons[week_index][day_index]
                if day_number == 0:
                    button.config(text="", state="disabled", bg="#111111")
                else:
                    button_date = datetime.date(self.current_year, self.current_month, day_number)
                    is_today = button_date == self.today
                    is_selected = button_date == self.selected_date
                    button.config(text=str(day_number), state="normal", fg="white")
                    if is_selected:
                        button.config(bg="#4a4aff")
                    elif is_today:
                        button.config(bg="#3d5a8f")
                    else:
                        button.config(bg="#1f1f1f")

        if self.selected_date.month != self.current_month or self.selected_date.year != self.current_year:
            self.selected_date = datetime.date(self.current_year, self.current_month, 1)
        self._update_event_display()

    # Show events for the selected day in the right panel.
    def _update_event_display(self):
        self.selected_label.config(text=f"Selected: {self.selected_date.strftime('%A, %B %d, %Y')}")

        date_key = self.selected_date.isoformat()
        events = self.events.get(date_key, [])
        alarms = self.alarms.get(date_key, [])

        self.event_listbox.delete(0, tk.END)
        if events:
            for event in events:
                self.event_listbox.insert(tk.END, event)
        else:
            self.event_listbox.insert(tk.END, "No events for this day")

        self.alarm_listbox.delete(0, tk.END)
        if alarms:
            sorted_alarms = sorted(alarms, key=lambda alarm: alarm["time"])
            for alarm in sorted_alarms:
                self.alarm_listbox.insert(tk.END, f"{alarm['time']} - {alarm['text']}")
        else:
            self.alarm_listbox.insert(tk.END, "No alarms for this day")

    # Handle clicking a day button in the calendar.
    def _select_day(self, week_index, day_index):
        month_calendar = calendar.monthcalendar(self.current_year, self.current_month)
        if week_index >= len(month_calendar):
            return

        day_number = month_calendar[week_index][day_index]
        if day_number == 0:
            return

        self.selected_date = datetime.date(self.current_year, self.current_month, day_number)
        self._update_calendar()
        self._update_event_display()

    # Add a new event for the selected day.
    def _add_event(self):
        event_text = self.event_entry.get().strip()
        if not event_text:
            return

        date_key = self.selected_date.isoformat()
        self.events.setdefault(date_key, []).append(event_text)
        self.event_entry.delete(0, tk.END)
        self._update_event_display()

    # Remove the event the user selected from the list.
    def _remove_event(self):
        selected_indices = self.event_listbox.curselection()
        if not selected_indices:
            return

        index = selected_indices[0]
        date_key = self.selected_date.isoformat()
        events = self.events.get(date_key, [])
        if not events or index >= len(events):
            return

        events.pop(index)
        if not events:
            self.events.pop(date_key, None)
        self._update_event_display()

    # Add a new alarm for the selected day using 24-hour time.
    def _add_alarm(self):
        alarm_time = self.alarm_time_entry.get().strip()
        alarm_text = self.alarm_text_entry.get().strip()
        if not alarm_time or not alarm_text:
            messagebox.showerror("Missing alarm", "Please enter both time and message for the alarm.")
            return

        try:
            parsed_time = datetime.datetime.strptime(alarm_time, "%H:%M").time()
        except ValueError:
            messagebox.showerror("Invalid time", "Use the 24-hour format HH:MM, for example 14:30.")
            return

        date_key = self.selected_date.isoformat()
        alarm = {
            "time": parsed_time.strftime("%H:%M"),
            "text": alarm_text,
            "triggered": False,
        }
        self.alarms.setdefault(date_key, []).append(alarm)
        self.alarm_time_entry.delete(0, tk.END)
        self.alarm_text_entry.delete(0, tk.END)
        self._update_event_display()

    # Remove the selected alarm from the list.
    def _remove_alarm(self):
        selected_indices = self.alarm_listbox.curselection()
        if not selected_indices:
            return

        index = selected_indices[0]
        date_key = self.selected_date.isoformat()
        alarms = self.alarms.get(date_key, [])
        if not alarms or index >= len(alarms):
            return

        alarms.pop(index)
        if not alarms:
            self.alarms.pop(date_key, None)
        self._update_event_display()

    # Check whether any alarms should go off for today.
    def _check_alarms(self):
        now = datetime.datetime.now()
        date_key = now.date().isoformat()
        today_alarms = self.alarms.get(date_key, [])
        updated = False

        for alarm in today_alarms:
            if alarm.get("triggered"):
                continue

            try:
                alarm_time = datetime.datetime.strptime(alarm["time"], "%H:%M").time()
            except ValueError:
                continue

            if now.time() >= alarm_time:
                messagebox.showinfo(
                    "Alarm",
                    f"Alarm for {now.strftime('%A, %B %d, %Y')} at {alarm['time']}: {alarm['text']}",
                )
                alarm["triggered"] = True
                updated = True

        if updated and self.selected_date.isoformat() == date_key:
            self._update_event_display()

        self.after(1000, self._check_alarms)

    # Show the previous month in the calendar.
    def _show_prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.selected_date = datetime.date(self.current_year, self.current_month, 1)
        self._update_calendar()

    # Show the next month in the calendar.
    def _show_next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.selected_date = datetime.date(self.current_year, self.current_month, 1)
        self._update_calendar()


if __name__ == "__main__":
    app = CalendarApp()
    app.mainloop()
