import json
import re
from typing import Dict, List, Any

def parse_markdown_faq(md_content: str) -> Dict[str, Any]:
    """
    Парсит Markdown FAQ и структурирует в семантические блоки для LLM
    """
    
    # Инициализация структуры
    knowledge_base = {
        "metadata": {
            "source": "globustele.com",
            "type": "esim_support_knowledge_base",
            "version": "1.0",
            "last_updated": "2024"
        },
        "service_overview": {
            "description": "",
            "key_features": [],
            "requirements": []
        },
        "compatibility": {
            "supported_devices": {
                "apple": {
                    "smartphones": [],
                    "tablets": []
                },
                "android": {
                    "samsung": [],
                    "google": [],
                    "other_brands": {}
                }
            },
            "general_requirements": []
        },
        "installation": {
            "methods": {
                "qr_code": {
                    "steps": [],
                    "tips": []
                },
                "manual": {
                    "steps": [],
                    "required_info": []
                }
            },
            "post_installation": [],
            "apn_settings": ""
        },
        "troubleshooting": {
            "connectivity": {
                "roaming_setup": [],
                "coverage_issues": [],
                "solutions": []
            },
            "common_problems": []
        },
        "account_management": {
            "balance_check": {
                "method": "",
                "ussd_code": ""
            },
            "top_up": []
        },
        "security_privacy": {
            "features": [],
            "advantages": [],
            "protection_details": []
        },
        "payment": {
            "methods": [],
            "process": []
        },
        "support": {
            "contact_methods": [],
            "response_time": "",
            "languages": []
        }
    }
    
    # Разбиваем контент на секции по заголовкам
    sections = re.split(r'^##\s+', md_content, flags=re.MULTILINE)
    
    for section in sections:
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        title = lines[0].strip() if lines else ""
        content = '\n'.join(lines[1:]) if len(lines) > 1 else ""
        
        # Обработка секции "What is eSIM?"
        if "What is eSIM" in title:
            # Извлекаем основное описание
            desc_match = re.search(r'^(.*?)(?=\n\n|\Z)', content, re.DOTALL)
            if desc_match:
                knowledge_base["service_overview"]["description"] = desc_match.group(1).strip()
            
            # Извлекаем ключевые особенности
            if "no identity verification" in content.lower():
                knowledge_base["service_overview"]["key_features"].append("No identity verification required")
            if "UK (+44) phone number" in content:
                knowledge_base["service_overview"]["key_features"].append("UK (+44) phone number for SMS")
            if "unrestricted Internet access" in content:
                knowledge_base["service_overview"]["key_features"].append("Unrestricted Internet access via European gateway")
            if "no user data" in content.lower():
                knowledge_base["security_privacy"]["features"].append("Complete privacy - no user data collection")
                
        # Обработка совместимых устройств
        elif "compatible devices" in title.lower():
            current_brand = ""
            current_category = ""
            
            for line in content.split('\n'):
                line = line.strip()
                
                # Определяем бренды и категории
                if line.startswith('### '):
                    current_brand = line.replace('###', '').strip().upper()
                elif line.startswith('#### '):
                    current_category = line.replace('####', '').strip().lower()
                elif line.startswith('##### '):
                    sub_brand = line.replace('#####', '').strip()
                    if current_brand == "ANDROID":
                        knowledge_base["compatibility"]["supported_devices"]["android"]["other_brands"][sub_brand] = []
                        current_brand = f"ANDROID_{sub_brand}"
                elif line and not line.startswith('#'):
                    # Добавляем устройства
                    device = line.strip()
                    
                    if current_brand == "APPLE":
                        if current_category == "smartphones":
                            knowledge_base["compatibility"]["supported_devices"]["apple"]["smartphones"].append(device)
                        elif current_category == "tablets":
                            knowledge_base["compatibility"]["supported_devices"]["apple"]["tablets"].append(device)
                    elif current_brand.startswith("ANDROID_"):
                        brand_name = current_brand.replace("ANDROID_", "")
                        if brand_name == "Samsung":
                            knowledge_base["compatibility"]["supported_devices"]["android"]["samsung"].append(device)
                        elif brand_name == "Google":
                            knowledge_base["compatibility"]["supported_devices"]["android"]["google"].append(device)
                        else:
                            if brand_name in knowledge_base["compatibility"]["supported_devices"]["android"]["other_brands"]:
                                knowledge_base["compatibility"]["supported_devices"]["android"]["other_brands"][brand_name].append(device)
        
        # Обработка оплаты
        elif "pay with a bank card" in title.lower():
            knowledge_base["payment"]["methods"].append("Bank card")
            knowledge_base["payment"]["process"].append(content.strip())
        
        # Обработка роуминга
        elif "data roaming" in title.lower():
            roaming_info = content.strip().replace('\n', ' ')
            knowledge_base["troubleshooting"]["connectivity"]["roaming_setup"].append(roaming_info)
            knowledge_base["installation"]["post_installation"].append("Enable Data Roaming in settings")
        
        # Обработка покрытия
        elif "coverage" in title.lower():
            coverage_tips = []
            for line in content.split('\n'):
                if line.strip():
                    coverage_tips.append(line.strip())
            knowledge_base["troubleshooting"]["connectivity"]["coverage_issues"] = coverage_tips
        
        # Обработка установки через QR
        elif "Option 1" in title or "scanning the QR" in title:
            steps = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    steps.append(line[2:])
                elif line and not line.startswith('#'):
                    if "scan the QR code with your iPhone Camera" in line:
                        knowledge_base["installation"]["methods"]["qr_code"]["tips"].append(line)
                    elif line:
                        steps.append(line)
            
            knowledge_base["installation"]["methods"]["qr_code"]["steps"] = steps
            
            # APN настройки
            if "APN settings" in content:
                knowledge_base["installation"]["apn_settings"] = "Check APN settings if required (details in SMS after purchase)"
        
        # Обработка ручной установки
        elif "Option 2" in title or "manually" in title.lower():
            manual_steps = []
            required_info = []
            
            for line in content.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    required_info.append(line)
                elif line.startswith('On iPhone'):
                    manual_steps.append(line)
                elif line and not line.startswith('#'):
                    manual_steps.append(line)
            
            knowledge_base["installation"]["methods"]["manual"]["steps"] = manual_steps
            knowledge_base["installation"]["methods"]["manual"]["required_info"] = required_info
        
        # Проверка баланса
        elif "check my balance" in title.lower():
            if "*187#" in title:
                knowledge_base["account_management"]["balance_check"]["ussd_code"] = "*187#"
            knowledge_base["account_management"]["balance_check"]["method"] = content.strip()
        
        # Безопасность
        elif "security" in title.lower():
            security_items = []
            for line in content.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    security_items.append(line)
                elif line and "IMEI" in line:
                    knowledge_base["security_privacy"]["protection_details"].append(line)
            
            if security_items:
                knowledge_base["security_privacy"]["advantages"] = security_items
    
    # Очистка пустых массивов и словарей (опционально)
    def clean_empty(d):
        if not isinstance(d, dict):
            return d
        return {k: clean_empty(v) for k, v in d.items() 
                if v and (not isinstance(v, (list, dict)) or v)}
    
    # Добавляем дополнительные поля для будущего расширения
    knowledge_base["examples"] = {
        "frequently_asked": [],
        "conversation_samples": []
    }
    
    knowledge_base["policies"] = {
        "refund": "",
        "support_hours": "",
        "activation_time": ""
    }
    
    knowledge_base["pricing"] = {
        "data_packages": [],
        "countries": {},
        "special_offers": []
    }
    
    return knowledge_base

def convert_md_to_json(input_file: str, output_file: str):
    """
    Конвертирует MD файл в структурированный JSON
    """
    try:
        # Читаем MD файл
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Парсим и структурируем
        knowledge_base = parse_markdown_faq(md_content)
        
        # Сохраняем в JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Успешно конвертировано: {input_file} -> {output_file}")
        
        # Выводим статистику
        device_count = (
            len(knowledge_base["compatibility"]["supported_devices"]["apple"]["smartphones"]) +
            len(knowledge_base["compatibility"]["supported_devices"]["apple"]["tablets"]) +
            len(knowledge_base["compatibility"]["supported_devices"]["android"]["samsung"]) +
            len(knowledge_base["compatibility"]["supported_devices"]["android"]["google"])
        )
        
        print(f"\n📊 Статистика:")
        print(f"  - Найдено устройств: {device_count}")
        print(f"  - Методов установки: {len(knowledge_base['installation']['methods'])}")
        print(f"  - Секций безопасности: {len(knowledge_base['security_privacy'])}")
        
        return knowledge_base
        
    except FileNotFoundError:
        print(f"❌ Файл не найден: {input_file}")
        return None
    except Exception as e:
        print(f"❌ Ошибка при конвертации: {str(e)}")
        return None

# Функция для добавления новой информации в существующую базу
def extend_knowledge_base(kb_file: str, new_data: Dict[str, Any], section: str):
    """
    Расширяет существующую базу знаний новыми данными
    
    Args:
        kb_file: путь к JSON файлу базы знаний
        new_data: новые данные для добавления
        section: раздел для добавления (pricing, examples, etc.)
    """
    with open(kb_file, 'r', encoding='utf-8') as f:
        kb = json.load(f)
    
    if section in kb:
        if isinstance(kb[section], dict):
            kb[section].update(new_data)
        elif isinstance(kb[section], list):
            kb[section].extend(new_data)
    else:
        kb[section] = new_data
    
    with open(kb_file, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)
    
    print(f"✅ База знаний обновлена: добавлен раздел '{section}'")

if __name__ == "__main__":
    # Запуск конвертации
    input_md = "globustelefaq.md"  # имя вашего MD файла
    output_json = "knowledge_base.json"
    
    # Конвертируем
    kb = convert_md_to_json(input_md, output_json)
    
    # Пример добавления новых данных (раскомментируйте при необходимости)
    """
    # Добавляем примеры цен
    pricing_data = {
        "data_packages": [
            {"size": "1GB", "validity": "7 days", "price": "$5"},
            {"size": "3GB", "validity": "30 days", "price": "$12"},
            {"size": "5GB", "validity": "30 days", "price": "$18"}
        ]
    }
    extend_knowledge_base(output_json, pricing_data, "pricing")
    
    # Добавляем примеры диалогов
    examples = {
        "frequently_asked": [
            {
                "question": "How to install eSIM on iPhone 14?",
                "answer": "Go to Settings → Cellular → Add Data Plan → Scan the QR code you received. Then enable Data Roaming."
            }
        ]
    }
    extend_knowledge_base(output_json, examples, "examples")
    """