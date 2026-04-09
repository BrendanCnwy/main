import json, random, tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any

class PaintApp:
    CANVAS_BG = "white"
    MAX_UNDO = 5
    WW, WH = 1800, 1400
    DRAW, OVER, LP = "drawable", "overlay", "layer::"
    TOOLS = {"brush":"Brush","eraser":"Eraser","spray":"Spray","rectangle":"Rect",
             "square":"Square","circle":"Circle","triangle":"Triangle","select":"Select","paste":"Paste"}

    def __init__(self, root):
        self.root = root
        root.title("Sketch Studio"); root.geometry("1120x720"); root.minsize(860,560); root.configure(bg="#eef2ff")
        self.tool = "brush"; self.color = "black"; self.color_name = "Black"
        self.lx = self.ly = self.sx = self.sy = self.preview = self.sel_rect = self.sel_bounds = None
        self.layers = ["Layer 1"]; self.hidden: set[str] = set(); self.lcnt = 1
        self.copied: list[dict] = []; self.undo: list[dict] = []
        self.sz_var = tk.IntVar(value=6); self.fb_var = tk.StringVar(); self.st_var = tk.StringVar(value="Ready.")
        self.wl_var = tk.StringVar(value="Pen width: 6"); self.tool_var = tk.StringVar(value="Brush")
        self.layer_var = tk.StringVar(value="Layer 1"); self.cbtns: dict[str,tk.Button] = {}
        self._styles(); self._layout(); self._refresh_layers(); self._bind(); self._fb()

    def _styles(self):
        s = ttk.Style()
        if "clam" in s.theme_names(): s.theme_use("clam")
        s.configure("App.TFrame", background="#eef2ff")
        s.configure("Panel.TFrame", background="#ffffff")
        for n,fg,f in [("Title","#111827",("Segoe UI",16,"bold")),("Body","#475467",("Segoe UI",9)),("Section","#1f2937",("Segoe UI",9,"bold"))]:
            s.configure(f"{n}.TLabel", background="#ffffff", foreground=fg, font=f)
        s.configure("Action.TButton", font=("Segoe UI",8,"bold"), padding=(6,4))

    def _layout(self):
        r = self.root; r.columnconfigure(0,weight=1); r.rowconfigure(0,weight=1)
        mf = ttk.Frame(r, padding=10, style="App.TFrame"); mf.grid(row=0,column=0,sticky="nsew")
        mf.columnconfigure(0,weight=1); mf.rowconfigure(1,weight=1)
        ctrl = ttk.Frame(mf, padding=10, style="Panel.TFrame"); ctrl.grid(row=0,column=0,sticky="ew",pady=(0,8))
        ctrl.columnconfigure(1,weight=1)
        ttk.Label(ctrl,text="Sketch Studio",style="Title.TLabel").grid(row=0,column=0,sticky="w",padx=(0,12))
        ttk.Label(ctrl,text="Colors, tools, layers, actions in one toolbar.",style="Body.TLabel",wraplength=560).grid(row=0,column=1,sticky="w")
        tb = ttk.Frame(ctrl,style="Panel.TFrame"); tb.grid(row=1,column=0,columnspan=2,sticky="ew",pady=(8,0)); tb.columnconfigure(4,weight=1)
        ttk.Label(tb,text="Colors",style="Section.TLabel").grid(row=0,column=0,sticky="w",padx=(0,6))
        cr = tk.Frame(tb,bg="#ffffff"); cr.grid(row=0,column=1,sticky="w",padx=(0,8))
        for i,(n,c) in enumerate([("Red","red"),("Green","green"),("Blue","blue"),("Black","black")]):
            b = tk.Button(cr,bg=c,activebackground=c,width=2,height=1,relief=tk.RAISED,bd=2,command=lambda v=c,l=n:self.set_color(v,l))
            b.grid(row=0,column=i,padx=(0,4),pady=1); self.cbtns[c]=b
        ttk.Button(tb,text="Custom…",command=self.custom_color,style="Action.TButton").grid(row=0,column=2,sticky="w",padx=(0,8))
        ttk.Label(tb,text="Tool",style="Section.TLabel").grid(row=0,column=3,sticky="w",padx=(0,6))
        self.tool_selector = ttk.Combobox(tb,textvariable=self.tool_var,values=tuple(self.TOOLS.values()),state="readonly",width=8)
        self.tool_selector.grid(row=0,column=4,sticky="w",padx=(0,8)); self.tool_selector.bind("<<ComboboxSelected>>",self._on_tool)
        ttk.Label(tb,text="Layer",style="Section.TLabel").grid(row=0,column=5,sticky="w",padx=(0,6))
        self.layer_cb = ttk.Combobox(tb,textvariable=self.layer_var,values=tuple(self.layers),state="readonly",width=11)
        self.layer_cb.grid(row=0,column=6,sticky="w",padx=(0,6)); self.layer_cb.bind("<<ComboboxSelected>>",self._on_layer)
        la = ttk.Frame(tb,style="Panel.TFrame"); la.grid(row=0,column=7,sticky="w",padx=(0,8))
        for i,(lbl,cmd) in enumerate([("+",self.add_layer),("Hide",self.toggle_vis),("↑",lambda:self.move_layer(1)),("↓",lambda:self.move_layer(-1)),("Del",self.del_layer)]):
            btn = ttk.Button(la,text=lbl,command=cmd,style="Action.TButton"); btn.grid(row=0,column=i,padx=1)
            if lbl=="Hide": self.hide_btn=btn
        ttk.Label(tb,textvariable=self.wl_var,style="Section.TLabel").grid(row=0,column=8,sticky="w",padx=(0,6))
        ttk.Scale(tb,from_=1,to=24,orient="horizontal",variable=self.sz_var,command=self._on_width).grid(row=0,column=9,sticky="ew",padx=(0,8))
        acts = ttk.Frame(tb,style="Panel.TFrame"); acts.grid(row=0,column=10,sticky="e")
        for i,(lbl,cmd) in enumerate([("Copy",self.copy_sel),("Paste",self.paste_sel),("Undo",self.undo_act),("Clear",self.clear),("Save",self.save),("Load",self.load)]):
            ttk.Button(acts,text=lbl,command=cmd,style="Action.TButton").grid(row=0,column=i,padx=2)
        sb = ttk.Frame(ctrl,style="Panel.TFrame"); sb.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(6,0))
        sb.columnconfigure(1,weight=1); sb.columnconfigure(2,weight=1)
        self.cprev = tk.Label(sb,text="   ",bg=self.color,relief=tk.SUNKEN,bd=1)
        self.cprev.grid(row=0,column=0,sticky="w",padx=(0,8))
        ttk.Label(sb,textvariable=self.fb_var,style="Body.TLabel",wraplength=320).grid(row=0,column=1,sticky="w")
        ttk.Label(sb,textvariable=self.st_var,style="Body.TLabel",wraplength=320).grid(row=0,column=2,sticky="w",padx=(10,0))
        cp = ttk.Frame(mf,padding=6,style="Panel.TFrame"); cp.grid(row=1,column=0,sticky="nsew")
        cp.columnconfigure(0,weight=1); cp.rowconfigure(0,weight=1)
        self.vsb = ttk.Scrollbar(cp,orient="vertical"); self.hsb = ttk.Scrollbar(cp,orient="horizontal")
        self.canvas = tk.Canvas(cp,bg=self.CANVAS_BG,highlightthickness=0,cursor="crosshair",
            xscrollcommand=self.hsb.set,yscrollcommand=self.vsb.set,scrollregion=(0,0,self.WW,self.WH))
        self.canvas.grid(row=0,column=0,sticky="nsew"); self.vsb.configure(command=self.canvas.yview)
        self.vsb.grid(row=0,column=1,sticky="ns"); self.hsb.configure(command=self.canvas.xview)
        self.hsb.grid(row=1,column=0,sticky="ew"); self._hilite()

    def _bind(self):
        c = self.canvas
        c.bind("<ButtonPress-1>",self.on_press); c.bind("<B1-Motion>",self.on_drag)
        c.bind("<ButtonRelease-1>",self.on_release); c.bind("<MouseWheel>",self._mw); c.bind("<Shift-MouseWheel>",self._smw)

    def _on_width(self,v): self.sz_var.set(int(float(v))); self.wl_var.set(f"Pen width: {self.sz_var.get()}")
    def _on_tool(self,_=None): self.set_tool(next((t for t,l in self.TOOLS.items() if l==self.tool_var.get()),self.tool)); self.tool_selector.selection_clear()
    def _on_layer(self,_=None): self.st_var.set(f"Active layer: {self.layer_var.get()}."); self._refresh_layers(); self._fb()
    def _ltag(self,l=None): return f"{self.LP}{l or self.layer_var.get()}"
    def _cv(self,e): return int(self.canvas.canvasx(e.x)),int(self.canvas.canvasy(e.y))
    def _mw(self,e): self.canvas.yview_scroll(-1 if e.delta>0 else 1,"units"); return "break"
    def _smw(self,e): self.canvas.xview_scroll(-1 if e.delta>0 else 1,"units"); return "break"

    def _refresh_layers(self):
        act = self.layer_var.get() if self.layer_var.get() in self.layers else self.layers[-1]
        self.layer_var.set(act)
        if hasattr(self,"layer_cb"): self.layer_cb.configure(values=tuple(self.layers))
        if hasattr(self,"hide_btn"): self.hide_btn.configure(text="Show" if act in self.hidden else "Hide")
        if not hasattr(self,"canvas"): return
        for l in self.layers:
            self.canvas.itemconfigure(self._ltag(l),state="hidden" if l in self.hidden else "normal")
            self.canvas.tag_raise(self._ltag(l))
        self.canvas.tag_raise(self.OVER)

    def add_layer(self):
        self._push()
        self.lcnt+=1
        while (n:=f"Layer {self.lcnt}") in self.layers: self.lcnt+=1
        self.layers.append(n); self.layer_var.set(n); self.st_var.set(f"Added {n}.")
        self._refresh_layers(); self._fb()

    def del_layer(self):
        if len(self.layers)==1: self.st_var.set("At least one layer must remain."); return
        self._push(); l=self.layer_var.get(); self.canvas.delete(self._ltag(l)); self.hidden.discard(l)
        i=self.layers.index(l); self.layers.remove(l); self.layer_var.set(self.layers[max(0,min(i,len(self.layers)-1))])
        self._clr_sel(); self.st_var.set(f"Deleted {l}."); self._refresh_layers(); self._fb()

    def toggle_vis(self):
        l=self.layer_var.get()
        if l in self.hidden: self.hidden.remove(l); msg=f"{l} visible."
        else: self.hidden.add(l); msg=f"{l} hidden."
        self.st_var.set(msg); self._refresh_layers(); self._fb()

    def move_layer(self,d):
        l=self.layer_var.get(); i=self.layers.index(l); ni=max(0,min(len(self.layers)-1,i+d))
        if ni==i: return
        self._push(); self.layers.insert(ni,self.layers.pop(i)); self.st_var.set(f"Moved {l} {'up' if d>0 else 'down'}."); self._refresh_layers()

    def set_tool(self,t):
        self.tool=t; self.tool_var.set(self.TOOLS.get(t,t.title()))
        self.st_var.set({"select":"Drag to select an area.","paste":"Click to place copied selection."}.get(t,"Ready to paint.")); self._fb()

    def set_color(self,c,n):
        self.color=c; self.color_name=n
        if self.tool in {"eraser","paste"}: self.tool="brush"
        self.st_var.set(f"Color: {n}."); self._hilite(); self._fb()

    def custom_color(self):
        _,h=colorchooser.askcolor(color=self.color,title="Choose color")
        if h: self.set_color(h,f"Custom ({h.upper()})")

    def copy_sel(self):
        ids=self._sel_ids()
        if not ids or self.sel_bounds is None: self.st_var.set("Select an area first."); return
        x1,y1,*_=self.sel_bounds
        self.copied=[self._ser(i,x1,y1) for i in ids]; self.st_var.set(f"Copied {len(self.copied)} item(s).")

    def paste_sel(self):
        if not self.copied: self.st_var.set("Nothing copied yet."); return
        self.set_tool("paste")

    def undo_act(self):
        if not self.undo: self.st_var.set("Undo history empty."); return
        self._restore(self.undo.pop()); self._clr_sel(); self.st_var.set("Undid last action.")

    def clear(self):
        if not self._ser_canvas(): self.st_var.set("Canvas already clear."); return
        self._push(); self.canvas.delete("all"); self.sel_rect=self.sel_bounds=self.preview=None; self.st_var.set("Cleared.")

    def save(self):
        p=filedialog.asksaveasfilename(title="Save",defaultextension=".json",filetypes=[("Sketch","*.json"),("All","*.*")])
        if not p: return
        try:
            with open(p,"w") as f: json.dump(dict(self._snap(),background=self.CANVAS_BG),f,indent=2)
        except OSError as e: messagebox.showerror("Save failed",str(e)); return
        self.st_var.set(f"Saved to {p}.")

    def load(self):
        p=filedialog.askopenfilename(title="Load",filetypes=[("Sketch","*.json"),("All","*.*")])
        if not p: return
        try:
            with open(p) as f: data=json.load(f)
        except (OSError,json.JSONDecodeError) as e: messagebox.showerror("Load failed",str(e)); return
        if not isinstance(data,(dict,list)): messagebox.showerror("Load failed","Invalid file."); return
        self._push(); self._restore(data); self.st_var.set(f"Loaded {p}.")

    def on_press(self,e):
        cx,cy=self._cv(e); self.lx=self.ly=None; self.sx=cx; self.sy=cy; self.lx=cx; self.ly=cy
        if self.tool in {"brush","eraser","spray"}:
            self._push()
            if self.tool=="spray": self._spray(cx,cy)
            else: self._seg(cx,cy,cx+1,cy+1)
        elif self.tool in {"rectangle","square","circle","triangle"}:
            self._push()
            if self.preview: self.canvas.delete(self.preview)
            self.preview=self._prev(cx,cy,cx,cy)
        elif self.tool=="select":
            self._clr_sel()
            self.sel_rect=self.canvas.create_rectangle(cx,cy,cx,cy,outline="#6366f1",dash=(4,2),width=2,tags=(self.OVER,"selection"))
            self.sel_bounds=None
        elif self.tool=="paste":
            self._push(); self._paste(cx,cy); self.set_tool("brush"); self.st_var.set("Pasted.")

    def on_drag(self,e):
        cx,cy=self._cv(e)
        if self.tool in {"brush","eraser"} and self.lx is not None:
            self._seg(self.lx,self.ly,cx,cy); self.lx=cx; self.ly=cy
        elif self.tool=="spray":
            self._spray(cx,cy); self.lx=cx; self.ly=cy
        elif self.tool in {"rectangle","square","circle","triangle"} and self.preview:
            self.canvas.coords(self.preview,*self._geom(self.sx,self.sy,cx,cy))
        elif self.tool=="select" and self.sel_rect:
            self.canvas.coords(self.sel_rect,self.sx,self.sy,cx,cy)

    def on_release(self,e):
        cx,cy=self._cv(e)
        if self.tool in {"rectangle","square","circle","triangle"} and self.preview:
            g=self._geom(self.sx,self.sy,cx,cy); self.canvas.delete(self.preview); self.preview=None; self._mkshape(g)
        if self.tool=="select" and self.sel_rect:
            self.sel_bounds=self._norm(*self.canvas.coords(self.sel_rect))
            self.st_var.set(f"{len(self._sel_ids())} item(s) selected.")
        self.lx=self.ly=self.sx=self.sy=None

    def _seg(self,x1,y1,x2,y2):
        c=self.CANVAS_BG if self.tool=="eraser" else self.color
        self.canvas.create_line(x1,y1,x2,y2,fill=c,width=self.sz_var.get(),capstyle=tk.ROUND,smooth=True,splinesteps=36,
            state="hidden" if self.layer_var.get() in self.hidden else "normal",tags=(self.DRAW,self._ltag()))
        self._refresh_layers()

    def _spray(self,x,y):
        r=max(6,self.sz_var.get()*2); ds=max(1,self.sz_var.get()//4); dc=max(10,self.sz_var.get()*2)
        for _ in range(dc):
            dx,dy=random.randint(-r,r),random.randint(-r,r)
            if dx*dx+dy*dy>r*r: continue
            self.canvas.create_oval(x+dx,y+dy,x+dx+ds,y+dy+ds,fill=self.color,outline=self.color,
                state="hidden" if self.layer_var.get() in self.hidden else "normal",tags=(self.DRAW,self._ltag()))
        self._refresh_layers()

    def _prev(self,x1,y1,x2,y2):
        fn={"rectangle":self.canvas.create_rectangle,"square":self.canvas.create_rectangle,
            "circle":self.canvas.create_oval,"triangle":self.canvas.create_polygon}[self.tool]
        return fn(*self._geom(x1,y1,x2,y2),outline=self.color,width=max(2,self.sz_var.get()//2),dash=(4,2),fill="",tags=(self.OVER,"preview"))

    def _mkshape(self,coords):
        {"rectangle":self.canvas.create_rectangle,"square":self.canvas.create_rectangle,
         "circle":self.canvas.create_oval,"triangle":self.canvas.create_polygon}[self.tool](
            *coords,outline=self.color,width=self.sz_var.get(),fill="",
            state="hidden" if self.layer_var.get() in self.hidden else "normal",tags=(self.DRAW,self._ltag()))
        self._refresh_layers()

    def _geom(self,x1,y1,x2,y2):
        if self.tool=="rectangle": return [x1,y1,x2,y2]
        if self.tool in {"square","circle"}:
            s=max(abs(x2-x1),abs(y2-y1))
            return [x1,y1,x1+(s if x2>=x1 else -s),y1+(s if y2>=y1 else -s)]
        l,r=sorted((x1,x2)); t,b=sorted((y1,y2))
        return [(l+r)/2,t,l,b,r,b]

    def _norm(self,x1,y1,x2,y2): l,r=sorted((x1,x2)); t,b=sorted((y1,y2)); return l,t,r,b

    def _sel_ids(self):
        if not self.sel_bounds: return []
        return [i for i in self.canvas.find_overlapping(*self.sel_bounds)
                if self.DRAW in self.canvas.gettags(i) and self.canvas.itemcget(i,"state")!="hidden"]

    def _paste(self,x,y):
        for d in self.copied: self._mkitem(d,x,y,self.layer_var.get())

    def _snap(self):
        return {"layers":self.layers[:],"hidden_layers":sorted(self.hidden),"active_layer":self.layer_var.get(),"items":self._ser_canvas()}

    def _push(self):
        s=self._snap()
        if self.undo and s==self.undo[-1]: return
        self.undo.append(s)
        if len(self.undo)>self.MAX_UNDO: self.undo.pop(0)

    def _ser_canvas(self): return [self._ser(i) for i in self.canvas.find_withtag(self.DRAW)]

    def _ser(self,iid,ox=0.0,oy=0.0):
        raw=self.canvas.coords(iid)
        coords=[v-ox if i%2==0 else v-oy for i,v in enumerate(raw)]
        layer=next((t.removeprefix(self.LP) for t in self.canvas.gettags(iid) if t.startswith(self.LP)),self.layers[0])
        opts={}
        for k in ("fill","outline","width","capstyle","smooth","splinesteps"):
            try:
                v=self.canvas.itemcget(iid,k)
                if v!="": opts[k]=v
            except tk.TclError: pass
        return {"type":self.canvas.type(iid),"coords":coords,"options":opts,"layer":layer}

    def _restore(self,snap):
        s=snap if isinstance(snap,dict) else {"items":snap,"layers":["Layer 1"],"hidden_layers":[],"active_layer":"Layer 1"}
        self.layers=list(s.get("layers") or ["Layer 1"]); self.hidden=set(s.get("hidden_layers",[]))
        self.lcnt=max([int(n.split()[-1]) for n in self.layers if n.startswith("Layer ") and n.split()[-1].isdigit()],default=len(self.layers))
        self.canvas.delete("all")
        for d in s.get("items",[]): self._mkitem(d)
        self.layer_var.set(s.get("active_layer",self.layers[-1]))
        if self.layer_var.get() not in self.layers: self.layer_var.set(self.layers[-1])
        self._clr_sel(); self.preview=None; self._refresh_layers()

    def _mkitem(self,d,ox=0.0,oy=0.0,ln=None):
        coords=[v+ox if i%2==0 else v+oy for i,v in enumerate(d.get("coords",[]))]
        fn=getattr(self.canvas,f"create_{d.get('type')}",None)
        l=ln or d.get("layer",self.layer_var.get())
        if l not in self.layers: self.layers.append(l)
        if fn: fn(*coords,**dict(d.get("options",{}),state="hidden" if l in self.hidden else "normal",tags=(self.DRAW,self._ltag(l))))

    def _clr_sel(self):
        if self.sel_rect: self.canvas.delete(self.sel_rect)
        self.sel_rect=self.sel_bounds=None

    def _hilite(self):
        for c,b in self.cbtns.items(): b.configure(relief=tk.SUNKEN if c==self.color else tk.RAISED,bd=3 if c==self.color else 2)

    def _fb(self):
        pc=self.CANVAS_BG if self.tool=="eraser" else self.color; l=self.layer_var.get()
        self.tool_var.set(self.TOOLS.get(self.tool,self.tool.title())); self.cprev.configure(bg=pc)
        self.fb_var.set(f"Tool: {self.TOOLS.get(self.tool,self.tool)} | Color: {self.color_name} | Layer: {l}{' (hidden)' if l in self.hidden else ''}")
        self._hilite()

if __name__=="__main__":
    root=tk.Tk(); PaintApp(root); root.mainloop()
