from pathlib import Path
import tempfile
import os
import base64

supported_img_type = {
    ".png",".jpg", ".jpeg",
}

def uploaded_img_to_content(uploaded_file):
      extension = Path (uploaded_file.name).suffix.lower()
      mime_types ={
            ".png":"image/png",
            ".jpg":"image/jpg",
            ".jpeg":"image/jpeg",
        }
      mime_type = mime_types.get(extension)
      if not mime_types:
            raise ValueError(f"Unsupported image format:{extension}")
      image_base64= base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
      return {
            "type":"image_url",
            "image_url":(
                  f"data:{mime_type};base64,{image_base64}"
            )
      }
