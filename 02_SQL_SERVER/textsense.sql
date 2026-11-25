-- TextSenseDB / SQL Server (SSMS) – một file SQL duy nhất.
-- Chạy toàn bộ script trước khi bật import dữ liệu hoặc ghi lịch sử huấn luyện từ notebook.
-- Import dữ liệu bằng pyodbc là tùy chọn; lịch sử huấn luyện được ghi vào dbo.TrainingRuns.
-- Toàn bộ lịch sử huấn luyện, dự đoán đơn và phân tích CSV/Excel đều lưu trong SQL Server.

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

-- PHẦN 3. LỊCH SỬ HUẤN LUYỆN (được ghi từ notebook qua pyodbc)
IF OBJECT_ID(N'dbo.TrainingRuns', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.TrainingRuns (
        TrainingRunID BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        StartedUtc DATETIMEOFFSET NOT NULL,
        Task NVARCHAR(40) NOT NULL,
        Status NVARCHAR(30) NOT NULL,
        ModelPath NVARCHAR(1000) NULL,
        Accuracy FLOAT NULL,
        MacroF1 FLOAT NULL,
        PrecisionPositive FLOAT NULL,
        RecallPositive FLOAT NULL,
        F1Positive FLOAT NULL,
        TestRows INT NULL,
        SelectedC FLOAT NULL,
        DecisionThreshold FLOAT NULL,
        PythonVersion NVARCHAR(50) NULL,
        SklearnVersion NVARCHAR(50) NULL,
        DataSha256 CHAR(64) NULL,
        ManifestSha256 CHAR(64) NULL,
        MetricsJson NVARCHAR(MAX) NULL,
        LogText NVARCHAR(MAX) NULL,
        CreatedAt DATETIMEOFFSET NOT NULL CONSTRAINT DF_TrainingRuns_CreatedAt DEFAULT SYSDATETIMEOFFSET()
    );
    CREATE INDEX IX_TrainingRuns_StartedUtc ON dbo.TrainingRuns(StartedUtc DESC);
END;
GO

-- PHẦN 4. LỊCH SỬ DỰ ĐOÁN VÀ PHÂN TÍCH TỆP (thay thế hoàn toàn SQLite)
IF OBJECT_ID(N'dbo.PredictionBatches', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.PredictionBatches (
        BatchID BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        CreatedUtc DATETIMEOFFSET NOT NULL CONSTRAINT DF_PredictionBatches_CreatedUtc DEFAULT SYSDATETIMEOFFSET(),
        Task NVARCHAR(40) NOT NULL,
        SourceName NVARCHAR(260) NOT NULL,
        [RowCount] INT NOT NULL CHECK ([RowCount] >= 0),
        UploadBytes BIGINT NOT NULL DEFAULT 0,
        UploadSha256 CHAR(64) NOT NULL
    );
    CREATE INDEX IX_PredictionBatches_CreatedUtc ON dbo.PredictionBatches(CreatedUtc DESC);
END;
GO

IF OBJECT_ID(N'dbo.Predictions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Predictions (
        PredictionID BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        BatchID BIGINT NOT NULL,
        RowNumber INT NOT NULL CHECK (RowNumber > 0),
        InputText NVARCHAR(MAX) NULL,
        PredictedLabel TINYINT NULL CHECK (PredictedLabel IN (0,1) OR PredictedLabel IS NULL),
        LabelName NVARCHAR(40) NULL,
        Status NVARCHAR(100) NOT NULL,
        CONSTRAINT FK_Predictions_PredictionBatches FOREIGN KEY (BatchID)
            REFERENCES dbo.PredictionBatches(BatchID) ON DELETE CASCADE,
        CONSTRAINT UQ_Predictions_Batch_Row UNIQUE (BatchID, RowNumber)
    );
    CREATE INDEX IX_Predictions_BatchID ON dbo.Predictions(BatchID, RowNumber);
END;
GO

-- PHẦN 4. BẢNG PHẢN HỒI KẾT QUẢ TỪ NGƯỜI DÙNG (USER FEEDBACK)
IF OBJECT_ID(N'dbo.UserFeedback', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserFeedback (
        FeedbackID BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        CreatedUtc DATETIMEOFFSET NOT NULL CONSTRAINT DF_UserFeedback_CreatedUtc DEFAULT SYSDATETIMEOFFSET(),
        SourceName NVARCHAR(40) NOT NULL,
        BatchID BIGINT NULL,
        RowNumber INT NULL,
        PredictionID BIGINT NULL,
        InputText NVARCHAR(MAX) NULL,
        InputSha256 CHAR(64) NULL,
        ModelPrediction NVARCHAR(100) NOT NULL,
        SuggestedLabel NVARCHAR(100) NOT NULL,
        ReasonCategory NVARCHAR(150) NOT NULL CONSTRAINT DF_UserFeedback_ReasonCategory DEFAULT N'Lý do khác',
        UserNote NVARCHAR(MAX) NULL,
        ReviewStatus NVARCHAR(40) NOT NULL CONSTRAINT DF_UserFeedback_ReviewStatus DEFAULT N'Chờ xem xét'
            CHECK (ReviewStatus IN (N'Chờ xem xét', N'Đã xác minh', N'Không chấp nhận')),
        ReviewedUtc DATETIMEOFFSET NULL,
        CONSTRAINT FK_UserFeedback_PredictionBatches FOREIGN KEY (BatchID)
            REFERENCES dbo.PredictionBatches(BatchID) ON DELETE SET NULL
    );
    CREATE INDEX IX_UserFeedback_CreatedUtc ON dbo.UserFeedback(CreatedUtc DESC);
    CREATE INDEX IX_UserFeedback_Status ON dbo.UserFeedback(ReviewStatus, CreatedUtc DESC);
END;
GO

-- Migration an toàn cho database đã tạo từ phiên bản trước (không xóa dữ liệu hiện có)
IF COL_LENGTH(N'dbo.UserFeedback', N'BatchID') IS NULL
    ALTER TABLE dbo.UserFeedback ADD BatchID BIGINT NULL;
IF COL_LENGTH(N'dbo.UserFeedback', N'RowNumber') IS NULL
    ALTER TABLE dbo.UserFeedback ADD RowNumber INT NULL;
IF COL_LENGTH(N'dbo.UserFeedback', N'PredictionID') IS NULL
    ALTER TABLE dbo.UserFeedback ADD PredictionID BIGINT NULL;
IF COL_LENGTH(N'dbo.UserFeedback', N'InputSha256') IS NULL
    ALTER TABLE dbo.UserFeedback ADD InputSha256 CHAR(64) NULL;
IF COL_LENGTH(N'dbo.UserFeedback', N'ReasonCategory') IS NULL
    ALTER TABLE dbo.UserFeedback ADD ReasonCategory NVARCHAR(150) NOT NULL CONSTRAINT DF_UserFeedback_ReasonCategory DEFAULT N'Lý do khác';
IF COL_LENGTH(N'dbo.UserFeedback', N'ReviewStatus') IS NULL
    ALTER TABLE dbo.UserFeedback ADD ReviewStatus NVARCHAR(40) NOT NULL
        CONSTRAINT DF_UserFeedback_ReviewStatus DEFAULT N'Chờ xem xét'
        CONSTRAINT CK_UserFeedback_ReviewStatus CHECK (ReviewStatus IN (N'Chờ xem xét', N'Đã xác minh', N'Không chấp nhận'));
IF COL_LENGTH(N'dbo.UserFeedback', N'ReviewedUtc') IS NULL
    ALTER TABLE dbo.UserFeedback ADD ReviewedUtc DATETIMEOFFSET NULL;
GO

IF INDEXPROPERTY(OBJECT_ID(N'dbo.UserFeedback'), N'IX_UserFeedback_Status', 'IndexId') IS NULL
    CREATE INDEX IX_UserFeedback_Status ON dbo.UserFeedback(ReviewStatus, CreatedUtc DESC);
GO

-- Xem lịch sử huấn luyện gần nhất
SELECT TOP (50) TrainingRunID, StartedUtc, Task, Status, Accuracy,
       F1Positive, TestRows, SelectedC, DecisionThreshold, ModelPath
FROM dbo.TrainingRuns
ORDER BY TrainingRunID DESC;
GO

-- PHẦN 5. KIỂM TRA SỐ DÒNG ĐÃ IMPORT
SELECT Source, COUNT_BIG(*) AS TotalRows
FROM dbo.Tweets GROUP BY Source ORDER BY Source;
SELECT COUNT_BIG(*) AS AllRows FROM dbo.Tweets;

-- PHẦN 6. THỐNG KÊ PHÂN BỐ NHÃN VÀ NGUỒN
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

-- PHẦN 7. TOP 20–30 TỪ LỚP 1
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

-- Xem lịch sử dự đoán gần nhất
SELECT TOP (50) BatchID, CreatedUtc, Task, SourceName, [RowCount], UploadBytes, UploadSha256
FROM dbo.PredictionBatches ORDER BY BatchID DESC;
GO

-- Xem tối đa 500 dòng của một batch (thay 1 bằng BatchID cần xem)
-- SELECT TOP (500) RowNumber, InputText, PredictedLabel, LabelName, Status
-- FROM dbo.Predictions WHERE BatchID = 1 ORDER BY RowNumber;

-- Xem danh sách phản hồi kết quả sai từ người dùng
SELECT TOP (50) FeedbackID, CreatedUtc, SourceName, ModelPrediction, SuggestedLabel, UserNote, InputText
FROM dbo.UserFeedback
ORDER BY FeedbackID DESC;
GO
