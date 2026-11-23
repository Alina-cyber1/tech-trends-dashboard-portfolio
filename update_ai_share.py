#!/usr/bin/env python3
"""
update_ai_share.py - Обновление AI Share
Считает долю УНИКАЛЬНЫХ патентов с G06N кодами
Запускается по расписанию каждый понедельник в 3:00
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AI_CPC_PREFIX = 'G06N'


def calculate_ai_share(cpc_path, patents_path, domain_name):
    logger.info(f"Обработка {domain_name}...")
    
    if not cpc_path.exists():
        logger.error(f"Файл CPC не найден: {cpc_path}")
        return 5
    
    if not patents_path.exists():
        logger.error(f"Файл патентов не найден: {patents_path}")
        return 5
    
    try:
        # Загружаем патенты
        patents_df = pd.read_parquet(patents_path, columns=['publication_number'])
        total_patents = len(patents_df)
        logger.info(f"Всего патентов: {total_patents}")
        
        # Загружаем CPC коды
        cpc_df = pd.read_parquet(cpc_path, columns=['publication_number', 'code'])
        
        # Находим уникальные патенты с AI классификацией
        ai_mask = cpc_df['code'].astype(str).str.startswith(AI_CPC_PREFIX, na=False)
        ai_patents = cpc_df[ai_mask]['publication_number'].unique()
        ai_count = len(ai_patents)
        
        ai_share = round(ai_count / total_patents * 100, 2) if total_patents > 0 else 0
        logger.info(f"{domain_name}: {ai_count} AI патентов из {total_patents} ({ai_share}%)")
        return ai_share
        
    except Exception as e:
        logger.error(f"Ошибка для {domain_name}: {e}")
        return 5


def main():
    logger.info("="*50)
    logger.info("Начинаем обновление AI Share...")
    logger.info(f"Время: {datetime.now()}")
    logger.info("="*50)
    
    results = {}
    
    results['semiconductors'] = calculate_ai_share(
        Path('/home/ubuntu/patents/semiconductors/cpc.parquet'),
        Path('/home/ubuntu/patents/semiconductors/patents.parquet'),
        "semiconductors"
    )
    
    results['gene_engineering'] = calculate_ai_share(
        Path('/home/ubuntu/patents/ge/cpc.parquet'),
        Path('/home/ubuntu/patents/ge/patents.parquet'),
        "gene_engineering"
    )
    
    results['last_update'] = datetime.now().isoformat()
    
    json_path = Path('/home/ubuntu/dashboard/ai_share.json')
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Результаты: semiconductors={results['semiconductors']}%, gene_engineering={results['gene_engineering']}%")
    logger.info("="*50)


if __name__ == "__main__":
    main()