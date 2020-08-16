import joblib
import numpy as np
from kivy.core.window import Window

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.config import Config

from kivy.uix.popup import Popup


import tkinter as tk
from tkinter import filedialog

from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib
import random

from kivy.core.image import Image as CoreImage
from PIL import Image
from io import BytesIO


class WindowManager(ScreenManager):
    def __init__(self, **kwargs):
        super(WindowManager, self).__init__(**kwargs)
        self.main_window = MainWindow()
        self.second_window = SecondWindow()
        self.add_widget(self.main_window)
        self.add_widget(self.second_window)
        
    def main_to_second(self):
        pic = self.main_window.main_panel.pil_image
        if(pic is None):
            return
        
        self.main_window.main_panel.crop()
        pic = self.main_window.main_panel.pil_image
        app = App.get_running_app()
        app.root.current = "second_window"
        app.root.transition.direction = 'left'
        self.second_window.second_panel.slider.value = 110
        self.second_window.second_panel.pil_image = pic
        self.second_window.second_panel.filter_and_plot(pic, 110)


class MainWindow(Screen):
    def __init__(self, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.main_panel = MainPanel()
        self.add_widget(self.main_panel)


class SecondWindow(Screen):
    def __init__(self, **kwargs):
        super(SecondWindow, self).__init__(**kwargs)
        self.second_panel = SecondPanel()
        self.add_widget(self.second_panel)
        self.second_panel._plot_init()


class SecondPanel(Widget):
    plot_field = ObjectProperty(None)
    slider = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(SecondPanel, self).__init__(**kwargs)
        self.model = joblib.load("models/forest.sav")
        self.scaler = joblib.load("models/scaler")
        
        self.pil_image = None
        
    def _plot_init(self):
        self.ids.plot_field.clear_widgets()
        plt.clf()
        self.ids.plot_field.add_widget(FigureCanvasKivyAgg(plt.gcf()))
        
    def filter_and_plot(self, photo, threshold):
        self.ids.plot_field.clear_widgets()
        plt.clf()
        clear_digit = filter_and_plot(photo, threshold)
        self.ids.plot_field.add_widget(FigureCanvasKivyAgg(plt.gcf()))
        
        return clear_digit
    
    def plot_test(self):
        self.ids.plot_field.clear_widgets()
        plt.clf()
        numbers = [random.randint(0, 20) for _ in range(10)]
        plt.plot(numbers)
        plt.ylabel('some numbers')
        
        self.ids.plot_field.add_widget(FigureCanvasKivyAgg(plt.gcf()))
           
    def analyze(self):
        if(self.pil_image is None):
            return
        
        transformed = self.scaler.transform(filter(self.pil_image, self.slider.value))
        result = self.model.predict(transformed)
        #print(result)
        show_popup(result)


class MainPanel(Widget):
    
    image = ObjectProperty(None)
    drawing_field = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(MainPanel, self).__init__(**kwargs)
        
        self.second_screen = SecondPanel()
        
        self.previous_image = None
        self.pil_image = None
        
        self.move_speed = 5
        self.size_increase = 5
        
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down, on_key_up=self._on_keyboard_up)
        
    def show_file_dialog(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(title="Select a file", filetypes=(("Images", ".jpg .jpeg .png"), ("All files", "*.*")))
        
        return file_path
         
    def get_image_position(self):
        X_POS = self.ids.image.center_x - self.ids.image.norm_image_size[0] / 2
        Y_POS = self.ids.image.center_y - self.ids.image.norm_image_size[1] / 2
        
        return (X_POS, Y_POS)
              
    def crop(self):
        if(self.pil_image is None):
            return     
    
        image_x, image_y = self.get_image_position()
        selection_x, selection_y = self.drawing_field.selection.pos[0], self.drawing_field.selection.pos[1]
        selection_size_x, selection_size_y = self.drawing_field.selection.size[0], self.drawing_field.selection.size[1]
        
        window_height = Window.size[1]
        
        # coordinate system root transformation from lower to upper right corner
        image_y = window_height - (image_y + self.ids.image.norm_image_size[1])
        selection_y = window_height - (selection_y + selection_size_y)
        
        image_scale = self.pil_image.size[0] / self.ids.image.norm_image_size[0]
        
        transformed_x = (selection_x - image_x) * image_scale
        transformed_y = (selection_y - image_y) * image_scale
        selection_size_x *= image_scale
        selection_size_y *= image_scale
          
        self.pil_image = self.pil_image.crop((transformed_x, transformed_y, transformed_x + selection_size_x, transformed_y + selection_size_y))
        
        self.display_pil_image()
        
        selection_x, selection_y = self.get_image_position()
        self.drawing_field.selection.pos = (selection_x, selection_y)
        self.drawing_field.selection.size[0] = self.ids.image.norm_image_size[0] 
        self.drawing_field.selection.size[1] = self.ids.image.norm_image_size[1] 
           
    def display_pil_image(self):
        data = BytesIO()
        self.pil_image.save(data, format='png')
        data.seek(0) 
        im = CoreImage(BytesIO(data.read()), ext='png')
        self.image.texture = im.texture 
        
    def load(self):
        file_name = (self.show_file_dialog())
        
        if(file_name == () or file_name == ""):
            return
        
        self.pil_image = Image.open(file_name)
        self.previous_image = self.pil_image
        self.display_pil_image()
        
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down, on_key_up=self._on_keyboard_up)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        
        if keycode[1] == 'right':
            self.drawing_field.selection.size[0] += self.size_increase
        elif keycode[1] == 'left':
            self.drawing_field.selection.size[0] -= self.size_increase 
        elif keycode[1] == 'up':
            self.drawing_field.selection.size[1] += self.size_increase    
        elif keycode[1] == 'down':
            self.drawing_field.selection.size[1] -= self.size_increase
        
        elif keycode[1] == 'r':
            if(self.previous_image is not None):
                self.pil_image = self.previous_image
                self.display_pil_image()
        elif keycode[1] == '1':
            self.pil_image = Image.open("photos/1.jpg")
            self.previous_image = self.pil_image
            self.display_pil_image()
        elif keycode[1] == '2':
            self.pil_image = Image.open("photos/2.jpg")
            self.previous_image = self.pil_image
            self.display_pil_image()
                
        elif keycode[1] in ['shift', 'rshift']:
            self.move_speed *= 5
            self.size_increase *= 5
            
        return True
            
    def _on_keyboard_up(self, keyboard, keycode):
        if keycode[1] in ['shift', 'rshift']:
            self.move_speed /= 5
            self.size_increase /= 5
        
        return True
        
         
class DrawingField(Widget):
    
    selection = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(DrawingField, self).__init__(**kwargs)
        
        self.move_speed = 5
        self.size_increase = 5

    def on_touch_down(self, touch):
         
        self.selection.pos = touch.pos
        self.selection.pos[0] -= self.selection.size[0] / 2
        self.selection.pos[1] -= self.selection.size[1] / 2
        
        if touch.button == 'scrolldown':
            self.selection.size[0] -= self.size_increase
            self.selection.size[1] -= self.size_increase
            
        elif touch.button == 'scrollup':
            self.selection.size[0] += self.size_increase
            self.selection.size[1] += self.size_increase
        
    def on_touch_move(self, touch):
        
        self.selection.pos = touch.pos
        self.selection.pos[0] -= self.selection.size[0] / 2
        self.selection.pos[1] -= self.selection.size[1] / 2


class LineRectangle(Widget):
    pass
   
    
class MyPopup(Popup):
    result_label = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(MyPopup, self).__init__(**kwargs)


class MainApp(App):

    def build(self):
        kv = Builder.load_file("design.kv")
        self.title = 'Hadwritten digit recognition'
        return kv


def filter_and_plot(image, threshold):

    clean = filter(image, threshold)
    digit_image = clean.reshape(28, 28)
    plt.imshow(digit_image, cmap=matplotlib.cm.binary, interpolation="nearest")
    plt.axis("off")
    
    return clean


def filter(image, threshold=110):
    
    small = image.convert('L').resize((28, 28))
    np_data = np.invert(np.reshape(small, (1, 784)))
    clean = np.where(np_data < threshold, 0, np_data)
    
    return clean
    
    
def show_popup(result):
    popupWindow = MyPopup()
    popupWindow.result_label.text = str(result)
    
    popupWindow.open()
   
    
def main():
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
    MainApp().run()
    

if __name__ == "__main__":  
    main()
    