from tkinter import *
import redis
import os
import random
import string

r = redis.Redis(host='localhost', port=6379, db=0)
p = r.pubsub()

# Unique token to separate the multiple instance runing concurently
# Needed for not sharing msg , books and channels entry
token = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
rmsg = "msg" + token
rbooks = "books" + token
rchannels = "channels" + token

#Main Redis functionalities:

"""
Publish a book in the hash with the isbn as key and {title , author , copies} as content
Send the isbn to all channels specified by the list description and also the author name
"""
def pub(isbn , title , author , copies , description):
    r.hset(isbn,mapping = {b'title':title,b'author':author,b'copies':copies})
    r.expire(isbn,3600) # 1h

    r.publish(author, isbn)
    for keyword in description.split(' '):
        r.publish(keyword, isbn)

"""
Subscribe to all elements of channels
"""
def sub(channel):
    p.subscribe(channel)

"""
Unsubscribe to channel
"""
def unsub(channel):
    p.unsubscribe(channel)

"""
Borrow a book if available
Decrement by 1 the copies of the book and reset the TTL
Return the hash entry corresponding to the book or an enmpty dict if not found
"""
def borrow(isbn):
    copies = r.hget(isbn,b'copies')
    if copies == None: #Not found
        return {}
    else:
        if(copies > b'0'):
            r.hincrby(isbn,b'copies',-1)
            r.expire(isbn,3600) # 1h
            return r.hgetall(isbn)
        else:
            raise ValueError('No book left')

"""
Increment by 1 the copies of one book and reset the TTL
"""
def return_book(isbn):
    if(r.hget(isbn,b'copies') != None): # If the book exist and has not expired
        r.hincrby(isbn,b'copies',1)
        r.expire(isbn,3600) # 1h

# Simple GUI

exitFlag = False
window = Tk()
window.title("Redis Pub/Sub")
window.geometry("1080x720")
window.minsize(480,360)
window.config(background='#973333')

icon = PhotoImage(file='logo.gif')
window.tk.call('wm', 'iconphoto', window._w, icon)

frame_top = Frame(window,bg='#973333')
frame_top_grid = Frame(window,bg='#973333')
frame_bottom = Frame(window,bg='#973333')
frame_bottom_grid = Frame(window,bg='#973333')

frame_list  = [frame_top,frame_top_grid,frame_bottom,frame_bottom_grid]

text_isbn = StringVar()
text_title = StringVar()
text_author = StringVar()
text_copies = StringVar()
text_desc = StringVar()
text_sub = StringVar()
text_borrow = StringVar()

#The link between the GUI and the actual redis functions:

def pub_gui():
    pub(text_isbn.get(),text_title.get(),text_author.get(),text_copies.get(),text_desc.get())
    text_isbn.set("")
    text_title.set("")
    text_author.set("")
    text_copies.set("")
    text_desc.set("")

def sub_gui():
    channel = text_sub.get()

    if not r.sismember(rchannels,channel): # Dont wont to sub multiple times to same channel
        sub(channel)
        r.sadd(rchannels,channel)

        text_sub.set("")
        pub_sub() # Reload the updated GUI

def unsub_gui(channel):
    unsub(channel.decode("utf-8"))
    r.srem(rchannels,channel)

    pub_sub() # Reload the updated GUI

def borrow_gui():
    try:
        isbn = text_borrow.get()
        book = borrow(isbn.encode())
        if book: # Empty dict evaluate to false
            r.rpush(rbooks, "isbn: "+ isbn + " , Title: " + book[b'title'].decode("utf-8") +\
             " , Author: "+ book[b'author'].decode("utf-8"))
            text_borrow.set("")
        else:
            text_borrow.set("Book expired or unavailable ")
        borrowed()  # Reload the updated GUI

    except ValueError:
        text_borrow.set("No book left")

def return_book_gui(i):

    return_book(r.lindex(rbooks,i).split(b' ')[1]) # Extract isbn number
    r.lset(rbooks, i, "DELETED") # To remove the book at correct index in case of
    r.lrem(rbooks, 1, "DELETED") # multiple copies
    borrowed() # Reload the updated GUI

def listen():
    m = p.get_message()
    if(m != None and r.hgetall(m['data'])): #Empty dict evaluate to false
        book = r.hgetall(m['data'])
        msg = "From channel "+ m['channel'].decode("utf-8") + " :  isbn: " + m['data'].decode("utf-8") + \
              ", Title: " + book[b'title'].decode("utf-8") + \
              ", Author: " + book[b'author'].decode("utf-8") + '\n'

        r.rpush(rmsg,msg)
        messages() # Open the messages tab to show new msg


#   pub_sub , subbed and borrow are the functions cleaning the tkinter window and
#   spawning one of the 2 main windows of the GUI
#   Probably not the best way to handle this

def pub_sub():
    for f in frame_list:
        for widget in f.winfo_children():
            widget.destroy()
        f.pack_forget()

    label_main = Label(frame_top,text= "Welcome to Pub/Sub",font=("Helvetica",40),bg='#973333',fg='white')
    label_main.pack()

    label_isbn = Label(frame_top_grid,text= "ISBN number",font=("Helvetica",10),bg='#973333',fg='white')
    label_isbn.grid(column = 0,row = 1)
    input_isbn = Entry(frame_top_grid,font=("Helvetica",10),bg='#973333',fg='white', textvariable=text_isbn)
    input_isbn.grid(column = 0,row = 2)
    label_title = Label(frame_top_grid,text= "Title",font=("Helvetica",10),bg='#973333',fg='white')
    label_title.grid(column = 1,row = 1,padx = 5)
    input_title = Entry(frame_top_grid,font=("Helvetica",10),bg='#973333',fg='white', textvariable=text_title)
    input_title.grid(column = 1,row = 2,padx = 5)
    label_author = Label(frame_top_grid,text= "Author",font=("Helvetica",10),bg='#973333',fg='white')
    label_author.grid(column = 2,row = 1,padx = 5)
    input_author = Entry(frame_top_grid,font=("Helvetica",10),bg='#973333',fg='white', textvariable=text_author)
    input_author.grid(column = 2,row = 2,padx = 5)
    label_copies = Label(frame_top_grid,text= "Number of copies",font=("Helvetica",10),bg='#973333',fg='white')
    label_copies.grid(column = 3,row = 1,padx = 5)
    input_copies = Entry(frame_top_grid,font=("Helvetica",10),bg='#973333',fg='white', textvariable=text_copies)
    input_copies.grid(column = 3,row = 2,padx = 5)
    label_desc = Label(frame_top_grid,text= "Book description",font=("Helvetica",10),bg='#973333',fg='white')
    label_desc.grid(column = 4,row = 1,padx = 5)
    input_desc = Entry(frame_top_grid,font=("Helvetica",10),bg='#973333',fg='white', textvariable=text_desc)
    input_desc.grid(column = 4,row = 2,padx = 5)

    pub_button = Button(frame_top_grid,text= "Pub",font=("Helvetica",15),bg='white',fg='#973333',command=pub_gui)
    pub_button.grid(column = 5,row = 2,padx = 5)

    label_sub = Label(frame_top_grid,text= "Channels to sub",font=("Helvetica",10),bg='#973333',fg='white')
    label_sub.grid(column = 0,row = 3)
    input_sub = Entry(frame_top_grid,font=("Helvetica",10),bg='#973333',fg='white', textvariable=text_sub)
    input_sub.grid(column = 0,row = 4)

    sub_button = Button(frame_top_grid,text= "Sub",font=("Helvetica",15),bg='white',fg='#973333',command=sub_gui)
    sub_button.grid(column = 1,row = 4,padx = 5)


    label_sub_list = Label(frame_bottom,text= "You are currently subbed to:",font=("Helvetica",30),bg='#973333',fg='white')
    label_sub_list.pack()



    i = 0
    for chan in r.smembers(rchannels):
        label = Label(frame_bottom_grid,text = chan.decode("utf-8"),font=("Helvetica",15),bg='#973333',fg='white')
        label.grid(column = 0,row = i,pady=5,sticky='W')
        unsub_button = Button(frame_bottom_grid,text= "Unsub",font=("Helvetica",15),bg='white',fg='#973333',command= lambda chan=chan: unsub_gui(chan))
        unsub_button.grid(column = 1,row = i,padx = 5)
        i+=1

    frame_top.pack(side='top')
    frame_top_grid.pack(side='top',pady=50)
    frame_bottom.pack(side=TOP, anchor=NW,padx=110)
    frame_bottom_grid.pack(side=TOP, anchor=NW,padx=110)

def borrowed():
    for f in frame_list:
        for widget in f.winfo_children():
            widget.destroy()
        f.pack_forget()

    label_borrow = Label(frame_top_grid,text= "Input ISBN",font=("Helvetica",10),bg='#973333',fg='white')
    label_borrow.grid(column = 0,row = 0)
    input_borrow = Entry(frame_top_grid,font=("Helvetica",10),bg='#973333',fg='white', textvariable=text_borrow)
    input_borrow.grid(column = 0,row = 1)

    button_borrow = Button(frame_top_grid,text= "Borrow book",font=("Helvetica",15),bg='white',fg='#973333',command=borrow_gui)
    button_borrow.grid(column = 1,row = 1,padx = 5)

    label_main = Label(frame_bottom,text= "You borrowed:",font=("Helvetica",25),bg='#973333',fg='white')
    label_main.pack()

    i = 0
    book = r.lindex(rbooks, i)
    while(book != None):
        label = Label(frame_bottom_grid,text= book.decode("utf-8"),font=("Helvetica",15),bg='#973333',fg='white')
        label.grid(column = 0,row = i,pady=5,sticky='W')
        button = Button(frame_bottom_grid,text= "Return",font=("Helvetica",15),bg='white',fg='#973333',command= lambda i=i: return_book_gui(i))
        button.grid(column = 1,row = i,pady=5,padx=5,sticky='W')
        i+= 1
        book = r.lindex(rbooks, i)

    frame_top_grid.pack(side='top')
    frame_bottom.pack(side='top',pady=15)
    frame_bottom_grid.pack(side='top')

def messages():
    for f in frame_list:
        for widget in f.winfo_children():
            widget.destroy()
        f.pack_forget()


    label_main = Label(frame_top,text= "You received:",font=("Helvetica",40),bg='#973333',fg='white')
    label_main.pack()

    i = 0
    msg = r.lindex(rmsg, i)
    while(msg != None):
        label = Label(frame_top_grid,text= msg.decode("utf-8"),font=("Helvetica",15),bg='#973333',fg='white')
        label.grid(column = 0,row = i,pady=5,sticky='W')
        i+=1
        msg = r.lindex(rmsg, i)

    frame_top.pack(side='top')
    frame_top_grid.pack(side='top')

def exit():
    global exitFlag
    exitFlag = True

menu_bar = Menu(window) #To navigate between the 2 tabs

file_menu = Menu(menu_bar,tearoff=0)
file_menu.add_command(label="Pub-Sub",command=pub_sub)
file_menu.add_command(label="Borrow-return",command=borrowed)
file_menu.add_command(label="Messages received",command=messages)
file_menu.add_command(label="Quit",command=exit)

menu_bar.add_cascade(label="Tabs",menu=file_menu)
window.config(menu=menu_bar)

pub_sub() #Default state of the GUI

while not exitFlag: # Main loop
    if(r.scard(rchannels) != 0):
        listen()
    window.update()

r.delete(rmsg) # Clear messages and subbed channels before closing
r.delete(rchannels)

j = 0
book = r.lindex(rbooks, j)
while(book != None):# Return all the books before closing
    return_book(book.split(b' ')[1])
    j+=1
    book = r.lindex(rbooks, j)


window.destroy()
