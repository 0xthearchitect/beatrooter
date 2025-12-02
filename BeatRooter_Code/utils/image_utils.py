import os
import json
from PIL import Image, PngImagePlugin, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QImage
import base64
from datetime import datetime

class ImageUtils:
    @staticmethod
    def load_image_metadata(file_path):
        metadata = {
            'file_size': '',
            'dimensions': '',
            'format': '',
            'exif_data': {},
            'png_info': {},
            'basic_info': {},
            'all_metadata': {}
        }
        
        try:
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            metadata['file_size'] = f"{file_size / 1024:.1f} KB"
            
            metadata['file_created'] = datetime.fromtimestamp(file_stats.st_ctime).isoformat()
            metadata['file_modified'] = datetime.fromtimestamp(file_stats.st_mtime).isoformat()

            with Image.open(file_path) as img:
                metadata['dimensions'] = f"{img.width} x {img.height}"
                metadata['format'] = img.format
                metadata['mode'] = img.mode
                metadata['basic_info'] = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size': f"{img.width}x{img.height}",
                    'aspect_ratio': f"{img.width/img.height:.2f}" if img.height > 0 else "N/A"
                }
                
                all_metadata = {}

                exif_data = ImageUtils._extract_exif_data(img)
                if exif_data:
                    all_metadata.update(exif_data)
                    metadata['exif_data'] = exif_data
                
                png_info = ImageUtils._extract_png_info(img)
                if png_info:
                    all_metadata.update(png_info)
                    metadata['png_info'] = png_info

                pil_info = ImageUtils._extract_pil_info(img)
                if pil_info:
                    all_metadata.update(pil_info)
                
                file_metadata = {
                    'file_size_bytes': file_size,
                    'file_size_human': metadata['file_size'],
                    'file_created': metadata['file_created'],
                    'file_modified': metadata['file_modified'],
                    'file_path': file_path,
                    'filename': os.path.basename(file_path)
                }
                all_metadata.update(file_metadata)
                
                metadata['all_metadata'] = all_metadata
                
                print(f"Metadados extraídos: {len(all_metadata)} campos")
                if exif_data:
                    print(f"EXIF: {len(exif_data)} tags")
                if png_info:
                    print(f"PNG: {len(png_info)} chunks")
                
        except Exception as e:
            print(f"Erro ao extrair metadados: {e}")
            metadata['error'] = str(e)
        
        return metadata
    
    @staticmethod
    def _extract_exif_data(img):
        exif_data = {}
        
        try:
            exif_dict = img.getexif()
            if exif_dict:
                for tag_id, value in exif_dict.items():
                    tag_name = TAGS.get(tag_id, f"Unknown_{tag_id}")
                    safe_value = ImageUtils._process_exif_value(value)
                    if safe_value is not None:
                        exif_data[tag_name] = safe_value
            
            if not exif_data and hasattr(img, '_getexif') and img._getexif():
                for tag_id, value in img._getexif().items():
                    tag_name = TAGS.get(tag_id, f"Unknown_{tag_id}")
                    safe_value = ImageUtils._process_exif_value(value)
                    if safe_value is not None:
                        exif_data[tag_name] = safe_value

            if exif_data and 'GPSInfo' in exif_data:
                gps_info = ImageUtils._extract_gps_info(exif_data['GPSInfo'])
                if gps_info:
                    exif_data['GPSInfo_parsed'] = gps_info
            
        except Exception as e:
            print(f"Erro ao extrair EXIF: {e}")
        
        return exif_data
    
    @staticmethod
    def _extract_png_info(img):
        png_info = {}
        
        try:
            if hasattr(img, 'text') and img.text:
                for key, value in img.text.items():
                    safe_value = ImageUtils._process_exif_value(value)
                    if safe_value is not None:
                        png_info[f"PNG_{key}"] = safe_value
            
            if hasattr(img, 'info'):
                for key, value in img.info.items():
                    if key not in ['exif', 'icc_profile']:
                        safe_value = ImageUtils._process_exif_value(value)
                        if safe_value is not None:
                            png_info[f"PNG_{key}"] = safe_value
            
        except Exception as e:
            print(f"Erro ao extrair PNG info: {e}")
        
        return png_info
    
    @staticmethod
    def _extract_pil_info(img):
        pil_info = {}
        
        try:
            pil_info['PIL_Format'] = img.format
            pil_info['PIL_Mode'] = img.mode
            pil_info['PIL_Size'] = f"{img.size[0]}x{img.size[1]}"
            pil_info['PIL_Width'] = img.size[0]
            pil_info['PIL_Height'] = img.size[1]
            
            if hasattr(img, 'filename'):
                pil_info['PIL_Filename'] = img.filename
            
            if hasattr(img, 'getbands'):
                pil_info['PIL_Bands'] = str(img.getbands())

            if hasattr(img, 'palette'):
                pil_info['PIL_Palette'] = str(img.palette.mode if img.palette else 'None')
            
        except Exception as e:
            print(f"Erro ao extrair PIL info: {e}")
        
        return pil_info
    
    @staticmethod
    def _extract_gps_info(gps_info):
        try:
            if not gps_info or not isinstance(gps_info, dict):
                return None
            
            gps_data = {}
            for key, value in gps_info.items():
                tag_name = GPSTAGS.get(key, f"GPS_{key}")
                safe_value = ImageUtils._process_exif_value(value)
                if safe_value is not None:
                    gps_data[tag_name] = safe_value
            
            if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                try:
                    lat = ImageUtils._convert_gps_coordinates(gps_data.get('GPSLatitude'))
                    lon = ImageUtils._convert_gps_coordinates(gps_data.get('GPSLongitude'))
                    if lat and lon:
                        gps_data['GPS_Latitude_Decimal'] = lat
                        gps_data['GPS_Longitude_Decimal'] = lon
                        gps_data['GPS_Coordinates'] = f"{lat}, {lon}"
                except:
                    pass
            
            return gps_data
        except Exception as e:
            print(f"Erro ao processar GPS: {e}")
            return None
    
    @staticmethod
    def _convert_gps_coordinates(coord):
        try:
            if not coord or not isinstance(coord, (list, tuple)) or len(coord) != 3:
                return None
            
            degrees, minutes, seconds = coord
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            return round(decimal, 6)
        except:
            return None
    
    @staticmethod
    def _process_exif_value(value):
        if value is None:
            return None
        
        try:
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8').strip()
                except:
                    try:
                        return value.decode('latin-1').strip()
                    except:
                        return f"0x{value.hex()}"
            
            elif isinstance(value, (int, float, bool)):
                return value
            
            elif isinstance(value, str):
                return value.strip()
            
            elif isinstance(value, (list, tuple)):
                if len(value) == 0:
                    return "[]"
                
                processed = []
                for item in value:
                    processed_item = ImageUtils._process_exif_value(item)
                    if processed_item is not None:
                        processed.append(processed_item)
                
                return str(processed) if processed else None
            
            elif isinstance(value, dict):
                processed_dict = {}
                for k, v in value.items():
                    processed_v = ImageUtils._process_exif_value(v)
                    if processed_v is not None:
                        processed_dict[str(k)] = processed_v
                return str(processed_dict) if processed_dict else None

            else:
                return str(value).strip()
                
        except Exception as e:
            print(f"Erro ao processar valor EXIF {type(value)}: {e}")
            return f"Error: {type(value)}"
    
    @staticmethod
    def image_to_base64(file_path):
        try:
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            return image_data
        except Exception as e:
            print(f"Erro ao converter imagem: {e}")
            return ""
    
    @staticmethod
    def get_supported_formats():
        return [
            "JPEG Files (*.jpg *.jpeg *.jpe)",
            "PNG Files (*.png)",
            "TIFF Files (*.tif *.tiff)",
            "BMP Files (*.bmp)",
            "GIF Files (*.gif)",
            "All Files (*)"
        ]