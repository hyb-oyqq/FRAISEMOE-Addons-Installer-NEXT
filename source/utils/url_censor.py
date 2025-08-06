import re

def censor_url(text):
    """Censors URLs in a given text string, replacing them with a protection message.
    
    Args:
        text: 要处理的文本
        
    Returns:
        str: 处理后的文本，URL被完全隐藏
    """
    if not isinstance(text, str):
        text = str(text)
    
    # 匹配URL并替换为固定文本
    url_pattern = re.compile(r'https?://[^\s/$.?#].[^\s]*')
    return url_pattern.sub('***URL protection***', text) 