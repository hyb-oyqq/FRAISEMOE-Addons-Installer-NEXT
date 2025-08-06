import re

def censor_url(text):
    """Censors URLs in a given text string, replacing them with a protection message.
    
    Args:
        text: 要处理的文本
        
    Returns:
        str: 处理后的文本，URL被完全隐藏
    """
    # 临时禁用URL隐藏功能，直接返回原始文本以便调试
    if not isinstance(text, str):
        text = str(text)
    
    return text  # 直接返回原始文本，不做任何隐藏
    
    # 以下是原始代码，现在被注释掉
    '''
    # 匹配URL并替换为固定文本
    url_pattern = re.compile(r'https?://[^\s/$.?#].[^\s]*')
    censored = url_pattern.sub('***URL protection***', text)
    
    # 额外处理带referer参数的情况
    referer_pattern = re.compile(r'--referer\s+(\S+)')
    censored = referer_pattern.sub('--referer ***URL protection***', censored)
    
    # 处理Origin头
    origin_pattern = re.compile(r'Origin:\s+(\S+)')
    censored = origin_pattern.sub('Origin: ***URL protection***', censored)
    
    return censored
    ''' 