import os
import sys
import logging
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from life_of_chairman_mao.config import settings

# 确保日志目录存在
os.makedirs(settings.LOGPATH, exist_ok=True)
LOG_FILE_PATH = os.path.join(settings.LOGPATH, 'all.log')


def verbose_formatter(verbose: int) -> str:
    """formatter factory"""
    if verbose is True:
        return 'verbose'
    return 'simple'


def update_log_level(debug: bool, level: str) -> str:
    """update log level"""
    if debug is True:
        level_num = logging.DEBUG
    else:
        level_num = logging.getLevelName(level)
    settings.set('LOGLEVEL', logging.getLevelName(level_num))
    return settings.LOGLEVEL


def init_log() -> None:
    """Init log config."""
    log_level = update_log_level(settings.DEBUG, str(settings.LOGLEVEL).upper())

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            'verbose': {
                'format': '%(asctime)s %(levelname)s %(name)s %(process)d %(thread)d %(message)s',
            },
            'simple': {
                'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
            },
        },
        "handlers": {
            "console": {
                "formatter": verbose_formatter(settings.VERBOSE),
                'level': 'DEBUG',
                "class": "logging.StreamHandler",
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': verbose_formatter(settings.VERBOSE),
                'filename': LOG_FILE_PATH,
                'maxBytes': 1024 * 1024 * 1024 * 200,  # 200M
                'backupCount': '5',
                'encoding': 'utf-8'
            },
        },
        "loggers": {
            '': {'level': log_level, 'handlers': ['console']},
        }
    }

    dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    """
    Gets a standard logger with a rich stream handler to stdout.
    Logger levels: NOTSET(0)\DEBUG(10)\INFO(20)\WARNING(30)\ERROR(40)\CRITICAL(50).
    """
    # 初始化日志配置
    init_log()
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    
    # 移除默认的控制台处理器
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RichHandler):
            root_logger.removeHandler(handler)
    
    # 创建并添加RichHandler
    rich_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)-9s - %(filename)-8s : %(lineno)s line - %(message)s", 
        datefmt="%m/%d/%Y %H:%M:%S"
    )
    
    rich_handler = RichHandler(show_time=False, show_path=False, keywords=["total", "packages", "Fetching"], rich_tracebacks=True)
    rich_handler.setFormatter(rich_formatter)
    rich_handler.setLevel(logging.INFO)
    
    root_logger.addHandler(rich_handler)
    
    # 返回特定名称的日志记录器
    return logging.getLogger(name)


logger = get_logger(__name__)


def test_logger():
    logger.debug('This is a customer debug message')
    logger.info('This is a customer info message')
    logger.warning('This is a customer warning message')
    logger.error('This is an customer error message')
    logger.critical('This is a customer critical message')
    try:
        3/0
    except Exception as e:
        logger.exception(e)
    
    
if __name__ == '__main__':
    test_logger()
