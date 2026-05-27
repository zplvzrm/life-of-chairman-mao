-- ============================================================
-- 教员的一生 · 数据库初始化脚本
-- 执行方式: mysql -u root -p < init_sql.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS jiaoyuan
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE jiaoyuan;

-- ------------------------------------------------------------
-- 年谱事件表
-- 对应 JSON 字段: age / year / month / day / do / annotation
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chronology (
    id         BIGINT        NOT NULL AUTO_INCREMENT        COMMENT '主键',
    age        INT           NOT NULL                       COMMENT '年龄',
    year       CHAR(4)       NOT NULL                       COMMENT '公历年份，如 1949',
    month      VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '月份（中文），如 正月',
    day        VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '日（中文），如 初一',
    event      TEXT          NOT NULL                       COMMENT '事件正文（对应 JSON 中的 do 字段）',
    annotation TEXT                                         COMMENT '注释 / 出处，可为空',

    PRIMARY KEY (id),
    INDEX idx_year       (year),
    INDEX idx_year_month (year, month),
    FULLTEXT INDEX ft_event (event)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '毛泽东年谱事件表';


-- ------------------------------------------------------------
-- 毛泽东选集表
-- 对应 JSON 字段: age / year / month / day / title / content / annotation / literature_id
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS selected_works (
    id            BIGINT        NOT NULL AUTO_INCREMENT        COMMENT '主键',
    age           INT           NOT NULL                       COMMENT '年龄',
    year          CHAR(4)       NOT NULL                       COMMENT '公历年份，如 1949',
    month         VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '月份（中文），如 正月',
    day           VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '日（中文），如 初一',
    title         TEXT          NOT NULL                       COMMENT '文章标题',
    content       MEDIUMTEXT    NOT NULL                       COMMENT '文章正文',
    annotation    MEDIUMTEXT                                   COMMENT '注释 / 出处，可为空',
    literature_id BIGINT        NULL                           COMMENT '文献 ID，关联 literature 表',

    PRIMARY KEY (id),
    INDEX idx_year          (year),
    INDEX idx_year_month    (year, month),
    INDEX idx_literature_id (literature_id),
    FULLTEXT INDEX ft_event (content)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '毛泽东选集表';


-- ------------------------------------------------------------
-- 毛泽东文集表
-- 对应 JSON 字段: age / year / month / day / title / content / annotation / literature_id
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collected_works (
    id            BIGINT        NOT NULL AUTO_INCREMENT        COMMENT '主键',
    age           INT           NOT NULL                       COMMENT '年龄',
    year          CHAR(4)       NOT NULL                       COMMENT '公历年份，如 1949',
    month         VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '月份（中文），如 正月',
    day           VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '日（中文），如 初一',
    title         TEXT          NOT NULL                       COMMENT '文章标题',
    content       MEDIUMTEXT    NOT NULL                       COMMENT '文章正文',
    annotation    MEDIUMTEXT                                   COMMENT '注释 / 出处，可为空',
    literature_id BIGINT        NULL                           COMMENT '文献 ID，关联 literature 表',

    PRIMARY KEY (id),
    INDEX idx_year          (year),
    INDEX idx_year_month    (year, month),
    INDEX idx_literature_id (literature_id),
    FULLTEXT INDEX ft_event (content)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '毛泽东文集表';


-- ------------------------------------------------------------
-- 建国以来毛泽东文稿表
-- 对应 JSON 字段: age / year / month / day / title / content / annotation / literature_id
-- literature_id 25–44 对应各册《建国以来毛泽东文稿》
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manuscript (
    id            BIGINT        NOT NULL AUTO_INCREMENT        COMMENT '主键',
    age           INT           NOT NULL                       COMMENT '年龄',
    year          CHAR(4)       NOT NULL                       COMMENT '公历年份，如 1949',
    month         VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '月份（中文），如 正月',
    day           VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '日（中文），如 初一',
    title         TEXT          NOT NULL                       COMMENT '文章标题',
    content       MEDIUMTEXT    NOT NULL                       COMMENT '文章正文',
    annotation    MEDIUMTEXT                                   COMMENT '注释 / 出处，可为空',
    literature_id BIGINT        NULL                           COMMENT '文献 ID，关联 literature 表',

    PRIMARY KEY (id),
    INDEX idx_year          (year),
    INDEX idx_year_month    (year, month),
    INDEX idx_literature_id (literature_id),
    FULLTEXT INDEX ft_event (content)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '建国以来毛泽东文稿表';


-- ------------------------------------------------------------
-- 用户浏览历史表
-- 每位匿名用户（UUID）只保留最后一次浏览记录
-- 通过 UNIQUE KEY(user_id) + ON DUPLICATE KEY UPDATE 实现 upsert
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_visits (
    id         BIGINT        NOT NULL AUTO_INCREMENT        COMMENT '主键',
    user_id    CHAR(36)      NOT NULL                       COMMENT '前端生成的匿名 UUID（v4）',
    year       CHAR(4)       NOT NULL                       COMMENT '最后浏览的年份',
    month      VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '最后浏览的月份',
    day        VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '最后浏览的日',
    visited_at DATETIME      NOT NULL
                             DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP    COMMENT '最后访问时间（自动更新）',

    PRIMARY KEY (id),
    UNIQUE KEY uk_user_id (user_id)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '用户最后一次浏览记录（匿名 UUID，每人一行）';


-- ------------------------------------------------------------
-- 文献资料表
-- 记录年谱事件所引用的原始文献信息
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS literature (
    id           BIGINT        NOT NULL AUTO_INCREMENT          COMMENT '主键',
    title        VARCHAR(512)  NOT NULL                         COMMENT '文献名称',
    author       VARCHAR(255)  NULL                             COMMENT '作者',
    publisher    VARCHAR(255)  NULL                             COMMENT '出版社',
    publish_year CHAR(4)       NULL                             COMMENT '出版年份',
    volume       VARCHAR(100)  NULL                             COMMENT '卷册信息，如 第一卷、上册',
    edition      VARCHAR(50)   NULL                             COMMENT '版次，如 第3版',
    isbn         VARCHAR(30)   NULL                             COMMENT 'ISBN 号',
    notes        TEXT          NULL                             COMMENT '备注（如收藏地、馆藏号等）',
    created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    PRIMARY KEY (id),
    INDEX idx_title (title(100)),
    INDEX idx_author (author)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '文献资料表';


-- 为 chronology 表增加文献关联列（幂等：列不存在才执行）
DROP PROCEDURE IF EXISTS _add_literature_id;
DELIMITER $$
CREATE PROCEDURE _add_literature_id()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'chronology'
          AND COLUMN_NAME  = 'literature_id'
    ) THEN
        ALTER TABLE chronology
            ADD COLUMN literature_id BIGINT NULL AFTER annotation;
        ALTER TABLE chronology
            ADD INDEX idx_literature_id (literature_id);
    END IF;
END$$
DELIMITER ;
CALL _add_literature_id();
DROP PROCEDURE IF EXISTS _add_literature_id;


-- ------------------------------------------------------------
-- 背景图片表
-- scene_type: 'home' = 首页星空背景, 'detail' = 年份详情页背景
-- year: 仅 scene_type='detail' 时有值，对应年份（如 1949）
-- image_url: 图片的外部 URL（优先）
-- image_data: 图片二进制数据（当无外部 URL 时使用 LONGBLOB 存储）
-- sort_order: 同一场景多张图片时的展示顺序
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS background_images (
    id          BIGINT        NOT NULL AUTO_INCREMENT          COMMENT '主键',
    scene_type  ENUM('home','detail') NOT NULL                COMMENT '场景类型：home=首页，detail=年份详情页',
    year        CHAR(4)       NULL                            COMMENT '年份，仅 scene_type=detail 时填写',
    image_url   VARCHAR(1024) NULL                            COMMENT '图片外部 URL（优先于 image_data）',
    image_data  LONGBLOB      NULL                            COMMENT '图片二进制数据（无外部 URL 时使用）',
    mime_type   VARCHAR(64)   NOT NULL DEFAULT 'image/jpeg'   COMMENT '图片 MIME 类型',
    title       VARCHAR(255)  NULL                            COMMENT '图片标题或描述（可选）',
    sort_order  INT           NOT NULL DEFAULT 0              COMMENT '同场景多图时的排序权重（升序）',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    PRIMARY KEY (id),
    INDEX idx_scene_year (scene_type, year),
    INDEX idx_scene_type (scene_type)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '背景图片表（首页 & 年份详情页）';
