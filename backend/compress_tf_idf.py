"""Text compression and summarization tool module (use TF-IDF to compress text)"""

import re
import jieba
import numpy as np
from typing import List, Dict, Any, Optional, Union
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer


class TextCompressor:
    """Text compressor class"""
    
    def __init__(self):
        self.setup_nltk_data()
        self.stemmer = PorterStemmer()
        
    def setup_nltk_data(self):
        """Download necessary NLTK data"""
        required_data = ['punkt', 'stopwords', 'punkt_tab']
        for data_name in required_data:
            try:
                nltk.data.find(f'tokenizers/{data_name}')
            except LookupError:
                try:
                    nltk.download(data_name, quiet=True)
                except Exception:
                    pass  # Silently handle download failures
    
    def detect_language(self, text: str) -> str:
        """Simple language detection"""
        # Count Chinese character ratio
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.findall(r'[\w\u4e00-\u9fff]', text))
        
        if total_chars == 0:
            return 'en'
            
        chinese_ratio = chinese_chars / total_chars
        return 'zh' if chinese_ratio > 0.3 else 'en'
    
    def preprocess_text(self, text: str, language: str = 'auto') -> Dict[str, Any]:
        """Preprocess text"""
        if language == 'auto':
            language = self.detect_language(text)
        
        # Clean text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Sentence segmentation
        if language == 'zh':
            sentences = re.split(r'[。！？；\n]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
        else:
            try:
                sentences = sent_tokenize(text)
            except:
                sentences = re.split(r'[.!?;\n]+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
        
        # Word tokenization
        if language == 'zh':
            words = list(jieba.cut(text))
            # Chinese stop words (simple list)
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        else:
            try:
                words = word_tokenize(text.lower())
                stop_words = set(stopwords.words('english'))
            except:
                words = re.findall(r'\b\w+\b', text.lower())
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall'}
        
        # Filter stop words and punctuation
        filtered_words = [word for word in words if word not in stop_words and len(word) > 1 and re.match(r'[\w\u4e00-\u9fff]+', word)]
        
        return {
            'original_text': text,
            'sentences': sentences,
            'words': words,
            'filtered_words': filtered_words,
            'language': language,
            'char_count': len(text),
            'word_count': len(filtered_words),
            'sentence_count': len(sentences)
        }
    
    
    def compress_by_ratio(self, text: str, compression_ratio: float = 0.6) -> Dict[str, Any]:
        """Compress text by ratio"""
        processed = self.preprocess_text(text)
        sentences = processed['sentences']
        
        if not sentences:
            return {
                'compressed_text': text,
                'compression_ratio': 0.0,
                'sentences_kept': 0,
                'sentences_total': 0
            }
        
        target_sentences = max(1, int(len(sentences) * compression_ratio))
        
        try:
            # Use TF-IDF to score sentences
            vectorizer = TfidfVectorizer(
                stop_words=None,
                lowercase=True,
                max_features=1000
            )
            
            tfidf_matrix = vectorizer.fit_transform(sentences)
            sentence_scores = np.sum(tfidf_matrix.toarray(), axis=1)
            
            # Select sentences with highest scores
            scored_sentences = [(i, score) for i, score in enumerate(sentence_scores)]
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            
            selected_indices = sorted([idx for idx, _ in scored_sentences[:target_sentences]])
            selected_sentences = [sentences[i] for i in selected_indices]
            
        except Exception:
            # Fallback: select longer sentences
            sentence_lengths = [(i, len(sentence)) for i, sentence in enumerate(sentences)]
            sentence_lengths.sort(key=lambda x: x[1], reverse=True)
            
            selected_indices = sorted([idx for idx, _ in sentence_lengths[:target_sentences]])
            selected_sentences = [sentences[i] for i in selected_indices]
        
        if processed['language'] == 'zh':
            compressed_text = '。'.join(selected_sentences)
        else:
            compressed_text = '. '.join(selected_sentences)
        
        actual_ratio = len(selected_sentences) / len(sentences)
        
        return {
            'compressed_text': compressed_text,
            'compression_ratio': round(actual_ratio, 4),
            'sentences_kept': len(selected_sentences),
            'sentences_total': len(sentences)
        }