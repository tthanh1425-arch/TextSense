-- TextSenseDB / SQL Server (SSMS) – một file SQL duy nhất.
-- Chạy phần 1–2 trước khi bật IMPORT_SQL_SERVER trong notebook.
-- Dữ liệu được import bằng pyodbc từ cả hai CSV đã làm sạch.
-- Không liên quan đến SQLite lưu lịch sử riêng ở ứng dụng web.

-- PHẦN 1. DATABASE
IF DB_ID(N'TextSenseDB') IS NULL
BEGIN
    EXEC(N'CREATE DATABASE TextSenseDB');
END;
GO
USE TextSenseDB;
GO

-- PHẦN 2. TABLES
IF OBJECT_ID(N'dbo.Tweets', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Tweets (
        TweetID BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Source NVARCHAR(40) NOT NULL,
        Content NVARCHAR(MAX) NOT NULL,
        OriginalLabel INT NOT NULL CHECK (OriginalLabel IN (-1,0,1)),
        BinaryLabel INT NOT NULL CHECK (BinaryLabel IN (0,1)),
        ImportedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT CK_TextSense_LabelMapping CHECK (
            (OriginalLabel = -1 AND BinaryLabel = 1) OR
            (OriginalLabel IN (0,1) AND BinaryLabel = 0)
        )
    );
    CREATE INDEX IX_Tweets_SourceLabel ON dbo.Tweets(Source, BinaryLabel);
END;
GO
IF OBJECT_ID(N'dbo.TweetTokens', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.TweetTokens (
        TweetID BIGINT NOT NULL,
        Token NVARCHAR(100) NOT NULL,
        Frequency INT NOT NULL CHECK (Frequency > 0),
        CONSTRAINT PK_TweetTokens PRIMARY KEY (TweetID, Token),
        CONSTRAINT FK_TweetTokens_Tweets FOREIGN KEY (TweetID)
            REFERENCES dbo.Tweets(TweetID) ON DELETE CASCADE
    );
END;
GO

-- PHẦN 3. KIỂM TRA SỐ DÒNG ĐÃ IMPORT
SELECT Source, COUNT_BIG(*) AS TotalRows
FROM dbo.Tweets GROUP BY Source ORDER BY Source;
SELECT COUNT_BIG(*) AS AllRows FROM dbo.Tweets;

-- PHẦN 4. THỐNG KÊ PHÂN BỐ NHÃN VÀ NGUỒN
SELECT Source, OriginalLabel, BinaryLabel, COUNT_BIG(*) AS Samples
FROM dbo.Tweets
GROUP BY Source, OriginalLabel, BinaryLabel
ORDER BY Source, OriginalLabel;
SELECT BinaryLabel, COUNT_BIG(*) AS Samples,
       CAST(100.0 * COUNT_BIG(*) / NULLIF((SELECT COUNT_BIG(*) FROM dbo.Tweets), 0) AS DECIMAL(8,2)) AS PercentOfAll
FROM dbo.Tweets GROUP BY BinaryLabel ORDER BY BinaryLabel;
SELECT Source,
       AVG(CAST(LEN(Content) AS FLOAT)) AS AvgCharacters,
       MIN(LEN(Content)) AS MinCharacters,
       MAX(LEN(Content)) AS MaxCharacters
FROM dbo.Tweets GROUP BY Source;

-- PHẦN 5. TOP 20–30 TỪ LỚP 1
-- Cách A: Khi đã bật IMPORT_TOKENS trong notebook, bảng TweetTokens được điền.
SELECT TOP (30) tt.Token, SUM(CAST(tt.Frequency AS BIGINT)) AS TotalFrequency
FROM dbo.TweetTokens AS tt
JOIN dbo.Tweets AS t ON t.TweetID = tt.TweetID
WHERE t.BinaryLabel = 1
GROUP BY tt.Token
ORDER BY TotalFrequency DESC, tt.Token;

-- Cách B: Không cần import TweetTokens, tách từ trực tiếp trên Tweets.
-- Dùng hàm STRING_SPLIT (SQL Server 2016+ / compatibility level 130+).
SELECT TOP (30) s.value AS Token, COUNT_BIG(*) AS TotalFrequency
FROM dbo.Tweets AS t
CROSS APPLY STRING_SPLIT(t.Content, N' ') AS s
WHERE t.BinaryLabel = 1 AND LEN(s.value) > 1
GROUP BY s.value
ORDER BY TotalFrequency DESC, s.value;
