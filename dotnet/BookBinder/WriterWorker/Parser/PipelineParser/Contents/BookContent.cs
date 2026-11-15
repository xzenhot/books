using System;
using System.Collections.Generic;
using System.Linq;

using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Parser.PipelineParser.Contents
{
    /// <summary>
    /// Everything read back out of a writer workspace folder: the plan (book.json), the
    /// progress report (progress.json), book level documents and every chapter/segment text file.
    /// </summary>
    internal sealed class BookContent
    {
        public string WorkspacePath { get; set; } = string.Empty;

        public BookModel? Plan { get; set; }

        public ProgressModel? Progress { get; set; }

        public List<ChapterContent> Chapters { get; } = new List<ChapterContent>();

        /// <summary>Book level markdown keyed by file name without extension (gist, storyline, style, ...).</summary>
        public Dictionary<string, string> Documents { get; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        public string? Title => Plan?.BookLongTitle ?? Plan?.BookName;

        /// <summary>Author of the book: book.json <c>user_name</c>, falling back to <c>updated_by</c>.</summary>
        public string? CreatedBy => Plan?.UserName ?? Plan?.UpdatedBy;

        /// <summary>Book creation date: book.json <c>created_at</c>, falling back to <c>updated_date</c>.</summary>
        public string? CreatedOn => Plan?.CreatedAt ?? Plan?.UpdatedDate;

        public string? BookName => Plan?.BookName;

        public string? Language => Plan?.Language;

        public string? Form => Plan?.Form;

        public int TotalWordCount => Chapters.Sum(chapter => chapter.WordCount);

        public int CompletedChapterCount => Chapters.Count(chapter => chapter.IsCompleted);

        public static BookContent Load(string workspacePath) => BookContentLoader.Load(workspacePath);

        public ChapterContent? GetChapter(int index) => Chapters.FirstOrDefault(chapter => chapter.Index == index);

        public ChapterContent? GetChapter(string name) =>
            Chapters.FirstOrDefault(chapter => string.Equals(chapter.Name, name, StringComparison.OrdinalIgnoreCase));

        /// <summary>
        /// Example: D:\lab\github\books\writer\workspaces\pipeline\nouka
        /// </summary>
        /// <param name="pipelineFolder"></param>
        public void Fill(string pipelineFolder)
        {
            BookContentLoader.Fill(this, pipelineFolder);
        }
    }
}
