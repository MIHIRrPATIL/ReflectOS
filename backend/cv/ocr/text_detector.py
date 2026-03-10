from paddleocr import PaddleOCR
import cv2
import numpy as np
import logging

# Suppress PaddleOCR logging
logging.getLogger("ppocr").setLevel(logging.ERROR)

import os 
# Force CPU usage to avoid kernel registration errors
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

class TextDetector:
    def __init__(self, lang='en', use_angle_cls=True):
        print("Initializing PaddleOCR...")
        try:
            # Initialize PaddleOCR
            # use_angle_cls=True enables orientation classification
            self.ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
            print("PaddleOCR initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize PaddleOCR: {e}")
            self.ocr = None

    def detect(self, frame):
        """
        Detects text in the given CV2 frame (BGR).
        Returns a list of results: [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], "text", confidence], ...]
        """
        if self.ocr is None:
            return []

        # PaddleOCR expects RGB or BGR? It handles BGR (cv2 default).
        # But usually libraries prefer RGB. Let's try passing BGR first as it's standard cv2.
        # PaddleOCR.ocr() accepts numpy array (image).
        
        try:
            # result = self.ocr.ocr(frame)
            # In some versions, result[0] is a list of lines.
            # In others (v2.7+ or specific models), it might be a dictionary.
            
            result = self.ocr.ocr(frame)
            
            if not result:
                return []
                
            # Check if result[0] is a dictionary (new format)
            if isinstance(result[0], dict):
                data = result[0]
                # Extract components
                boxes = data.get('dt_polys', []) # or 'rec_boxes'
                texts = data.get('rec_texts', [])
                scores = data.get('rec_scores', [])
                
                # Zip into expected format: [[box, (text, score)], ...]
                formatted_result = []
                for box, text, score in zip(boxes, texts, scores):
                    formatted_result.append([box, (text, score)])
                    
                # print(f"OCR Found {len(formatted_result)} text blocks (Dict format).")
                return formatted_result
                
            # Legacy format: result[0] is a list of [box, (text, score)]
            elif isinstance(result[0], list):
                # print(f"OCR Found {len(result[0])} text blocks (List format).")
                return result[0]
                
            return []
        except Exception as e:
            print(f"OCR Detection Error: {e}")
            return []

    def visualize(self, frame, results):
        """
        Draws bounding boxes and text on the frame.
        """
        image_copy = frame.copy()
        
        for line in results:
            # line structure: [box, (text, score)]
            # box: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            try:
                box = np.array(line[0]).astype(np.int32)
            except Exception as e:
                print(f"Error converting box: {line[0]} - {e}")
                continue
            text, score = line[1]
            
            # Draw polygon
            cv2.polylines(image_copy, [box], True, (0, 255, 0), 2)
            
            # Draw text
            # Use top-left corner of the box
            x, y = box[0]
            cv2.putText(image_copy, f"{text} ({score:.2f})", (int(x), int(y) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
        return image_copy
