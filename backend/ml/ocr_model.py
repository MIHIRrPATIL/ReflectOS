import os
import cv2
import numpy as np
from paddleocr import PaddleOCR

# Singleton for OCR to avoid reloading model
class OCRHandler:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        print("Initializing PaddleOCR...")
        # use_angle_cls=True for better accuracy on rotated text
        # lang='en' by default
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en') 
        print("PaddleOCR Initialized.")

    def process_image(self, img_array):
        """
        :param img_array: numpy array (cv2 format)
        :return: raw text string
        """
        result = self.ocr.ocr(img_array)
        # result is a list of lists (one per line?)
        # Structure: [[ [ [[x,y],...], (text, conf) ], ... ]]
        
        full_text = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                full_text.append(text)
        
        return "\n".join(full_text)

    def process_item(self, img_array, bbox=None):
        """
        :param bbox: [x1, y1, x2, y2]
        """
        if bbox:
            x1, y1, x2, y2 = map(int, bbox)
            # Crop
            img_array = img_array[y1:y2, x1:x2]
            
        return self.process_image(img_array)
