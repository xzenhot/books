using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;

using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Parser.PipelineParser.Contents
{
    /// <summary>
    /// Fills a <see cref="BookContent"/> from a writer workspace folder, for example
    /// <c>...\workspaces\pipeline\nouka</c>:
    /// <list type="bullet">
    /// <item><c>book.json</c> and <c>progress.json</c> for plan and status.</item>
    /// <item><c>chapters/{n}/chapter.json</c> + <c>chapter.md</c> + <c>context.md</c>.</item>
    /// <item><c>chapters/{n}/segments/{i}/segment.json</c> and the latest/editor/writer/translator/version texts.</item>
    /// <item><c>filters/quality/{n}/draft.md</c> as the pre-filter chapter draft.</item>
    /// </list>
    /// Missing files are skipped, so partially generated workspaces still load.
    /// </summary>
    internal static class BookContentLoader
    {
        private static readonly JsonSerializerOptions JsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };

        private static readonly string[] BookDocuments =
        [
            "bookseed.md",
            "gist.md",
            "override.md",
            "README.md",
            "signature.md",
            "storyline.md",
            "style.md",
        ];

        public static BookContent Load(string workspacePath)
        {
            var content = new BookContent();
            content.Fill(workspacePath);
            return content;
        }

        internal static void Fill(BookContent content, string workspacePath)
        {
            ArgumentNullException.ThrowIfNull(content);

            if (string.IsNullOrWhiteSpace(workspacePath))
            {
                throw new ArgumentException("A workspace folder is required.", nameof(workspacePath));
            }

            var root = Path.GetFullPath(workspacePath);
            if (!Directory.Exists(root))
            {
                throw new DirectoryNotFoundException($"Workspace folder not found: {root}");
            }

            var chaptersDirectory = Path.Combine(root, "chapters");
            var bookFile = Path.Combine(root, "book.json");
            if (!File.Exists(bookFile) && !Directory.Exists(chaptersDirectory))
            {
                throw new InvalidOperationException($"Not a writer workspace (no book.json or chapters folder): {root}");
            }

            content.WorkspacePath = root;
            content.Plan = ReadJson<BookModel>(bookFile);
            content.Progress = ReadJson<ProgressModel>(Path.Combine(root, "progress.json"));

            content.Chapters.Clear();
            content.Documents.Clear();

            foreach (var document in BookDocuments)
            {
                var text = ReadText(Path.Combine(root, document));
                if (text is not null)
                {
                    content.Documents[Path.GetFileNameWithoutExtension(document)] = text;
                }
            }

            foreach (var chapter in LoadChapters(root, chaptersDirectory, content.Plan, content.Progress))
            {
                content.Chapters.Add(chapter);
            }
        }

        /// <summary>Author recorded in book.json, shown as "created by" on every chapter and segment.</summary>
        private static string? PlanAuthor(BookModel? plan) => FirstNonEmpty(plan?.UserName, plan?.UpdatedBy);

        private static IEnumerable<ChapterContent> LoadChapters(
            string root,
            string chaptersDirectory,
            BookModel? plan,
            ProgressModel? progress)
        {
            if (!Directory.Exists(chaptersDirectory))
            {
                return plan?.Chapters.Select(chapter => FromPlan(chapter, PlanAuthor(plan))).ToList() ?? [];
            }

            var author = PlanAuthor(plan);
            var directories = OrderChapterDirectories(chaptersDirectory, progress);
            return directories.Select(directory => LoadChapter(root, directory, plan, progress, author)).ToList();
        }

        /// <summary>progress.json defines the reading order (Introduction, 1..n, Conclusion); otherwise numeric first.</summary>
        private static List<string> OrderChapterDirectories(string chaptersDirectory, ProgressModel? progress)
        {
            var directories = Directory.GetDirectories(chaptersDirectory)
                .OrderBy(directory => NumericOrder(Path.GetFileName(directory)))
                .ThenBy(directory => Path.GetFileName(directory), StringComparer.OrdinalIgnoreCase)
                .ToList();

            if (progress is null || progress.Chapters.Count == 0)
            {
                return directories;
            }

            var order = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            for (var position = 0; position < progress.Chapters.Count; position++)
            {
                var number = progress.Chapters[position].ChapterNumber;
                if (!string.IsNullOrWhiteSpace(number))
                {
                    order.TryAdd(number, position);
                }
            }

            return directories
                .OrderBy(directory => order.TryGetValue(Path.GetFileName(directory), out var position) ? position : int.MaxValue)
                .ThenBy(directory => NumericOrder(Path.GetFileName(directory)))
                .ThenBy(directory => Path.GetFileName(directory), StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static ChapterContent LoadChapter(
            string root,
            string directory,
            BookModel? plan,
            ProgressModel? progress,
            string? author)
        {
            var folder = Path.GetFileName(directory);
            var chapterFile = ReadJson<ChapterFileModel>(Path.Combine(directory, "chapter.json"));
            var index = chapterFile?.ChapterIndex ?? ParseIndex(folder);

            var planChapter = plan?.Chapters.FirstOrDefault(chapter => chapter.ChapterIndex == index)
                ?? plan?.Chapters.FirstOrDefault(chapter => string.Equals(chapter.Name, folder, StringComparison.OrdinalIgnoreCase));
            var progressChapter = FindProgressChapter(progress, folder, index);

            var chapter = new ChapterContent
            {
                Directory = directory,
                Index = index,
                Name = FirstNonEmpty(chapterFile?.Name, folder) ?? folder,
                Title = FirstNonEmpty(chapterFile?.ChapterTitle, planChapter?.ChapterTitle),
                Summary = FirstNonEmpty(chapterFile?.ChapterSummary, planChapter?.ChapterSummary),
                State = chapterFile?.State,
                Status = progressChapter?.Status,
                CompletedDate = progressChapter?.CompletedDate,
                CreatedBy = author,
                CreatedOn = progressChapter?.CompletedDate,
                FilePath = progressChapter?.FilePath,
                WordTarget = chapterFile?.WordTarget ?? planChapter?.WordTarget ?? 0,
                Markdown = ReadText(Path.Combine(directory, "chapter.md")),
                Context = ReadText(Path.Combine(directory, "context.md")),
                Draft = ReadText(Path.Combine(root, "filters", "quality", folder, "draft.md")),
            };

            var references = chapterFile?.FurtherReferences is { Count: > 0 } fileReferences
                ? fileReferences
                : planChapter?.FurtherReferences ?? [];
            chapter.FurtherReferences.AddRange(references);

            foreach (var segment in LoadSegments(directory, chapterFile, planChapter, author, chapter.CreatedOn))
            {
                chapter.Segments.Add(segment);
            }

            var markdownWords = CountWords(chapter.Markdown);
            chapter.WordCount = markdownWords > 0 ? markdownWords : chapter.Segments.Sum(segment => segment.WordCount);
            return chapter;
        }

        private static IEnumerable<SegmentContent> LoadSegments(
            string chapterDirectory,
            ChapterFileModel? chapterFile,
            ChapterModel? planChapter,
            string? author,
            string? createdOn)
        {
            var segmentsDirectory = Path.Combine(chapterDirectory, "segments");
            if (!Directory.Exists(segmentsDirectory))
            {
                return MetadataOnlySegments(chapterFile, planChapter, author, createdOn);
            }

            return Directory.GetDirectories(segmentsDirectory)
                .OrderBy(directory => NumericOrder(Path.GetFileName(directory)))
                .Select(directory => LoadSegment(directory, planChapter, author, createdOn))
                .ToList();
        }

        private static SegmentContent LoadSegment(
            string directory,
            ChapterModel? planChapter,
            string? author,
            string? createdOn)
        {
            var folder = Path.GetFileName(directory);
            var segmentFile = ReadJson<SegmentFileModel>(Path.Combine(directory, "segment.json"));
            var index = segmentFile?.SegmentIndex ?? ParseIndex(folder);
            var planSegment = planChapter?.Segments.FirstOrDefault(segment => segment.SegmentIndex == index);

            var segment = new SegmentContent
            {
                Directory = directory,
                Index = index,
                Name = FirstNonEmpty(segmentFile?.Name, folder) ?? folder,
                Title = FirstNonEmpty(segmentFile?.SegmentTitle, planSegment?.SegmentTitle),
                Summary = FirstNonEmpty(segmentFile?.SegmentSummary, planSegment?.SegmentSummary),
                State = segmentFile?.State,
                CreatedBy = author,
                CreatedOn = createdOn,
                WordTarget = segmentFile?.WordTarget ?? planSegment?.WordTarget ?? 0,
                LatestText = ReadStageText(Path.Combine(directory, "latest")),
                SegmentText = ReadText(Path.Combine(directory, "segment.md")),
                WriterText = ReadStageText(Path.Combine(directory, "writer")),
                EditorText = ReadStageText(Path.Combine(directory, "editor")),
                TranslatedText = ReadStageText(Path.Combine(directory, "translator")),
            };

            var references = segmentFile?.FurtherReferences is { Count: > 0 } fileReferences
                ? fileReferences
                : planSegment?.FurtherReferences ?? [];
            segment.FurtherReferences.AddRange(references);

            segment.EditorVersions.AddRange(ReadVersions(Path.Combine(directory, "editor", "version")));
            segment.Versions.AddRange(ReadVersions(Path.Combine(directory, "version")));
            segment.WordCount = CountWords(segment.Text);
            return segment;
        }

        private static IEnumerable<SegmentContent> MetadataOnlySegments(
            ChapterFileModel? chapterFile,
            ChapterModel? planChapter,
            string? author,
            string? createdOn)
        {
            if (chapterFile?.Segments is { Count: > 0 } fileSegments)
            {
                return fileSegments
                    .Select(segment => new SegmentContent
                    {
                        Index = segment.SegmentIndex ?? ParseIndex(segment.Name),
                        Name = segment.Name ?? string.Empty,
                        Title = segment.SegmentTitle,
                        Summary = segment.SegmentSummary,
                        State = segment.State,
                        CreatedBy = author,
                        CreatedOn = createdOn,
                        WordTarget = segment.WordTarget ?? 0,
                    })
                    .ToList();
            }

            if (planChapter?.Segments is { Count: > 0 } planSegments)
            {
                return planSegments
                    .Select(segment => new SegmentContent
                    {
                        Index = segment.SegmentIndex,
                        Name = segment.Name ?? string.Empty,
                        Title = segment.SegmentTitle,
                        Summary = segment.SegmentSummary,
                        CreatedBy = author,
                        CreatedOn = createdOn,
                        WordTarget = segment.WordTarget,
                    })
                    .ToList();
            }

            return [];
        }

        private static ChapterContent FromPlan(ChapterModel chapter, string? author)
        {
            var content = new ChapterContent
            {
                Index = chapter.ChapterIndex,
                Name = chapter.Name ?? chapter.ChapterIndex.ToString(CultureInfo.InvariantCulture),
                Title = chapter.ChapterTitle,
                Summary = chapter.ChapterSummary,
                CreatedBy = author,
                WordTarget = chapter.WordTarget,
            };

            content.FurtherReferences.AddRange(chapter.FurtherReferences);
            foreach (var segment in chapter.Segments)
            {
                content.Segments.Add(new SegmentContent
                {
                    Index = segment.SegmentIndex,
                    Name = segment.Name ?? string.Empty,
                    Title = segment.SegmentTitle,
                    Summary = segment.SegmentSummary,
                    CreatedBy = author,
                    WordTarget = segment.WordTarget,
                });
            }

            return content;
        }

        /// <summary>Reads segment_v1.md / chapter_v2.md style snapshots, ordered by version number.</summary>
        private static List<SegmentVersion> ReadVersions(string directory)
        {
            if (!Directory.Exists(directory))
            {
                return [];
            }

            return Directory.GetFiles(directory, "*.md")
                .Select(path => new SegmentVersion
                {
                    Version = ParseVersion(Path.GetFileNameWithoutExtension(path)),
                    Path = path,
                    Text = ReadText(path),
                })
                .Where(version => version.Text is not null)
                .OrderBy(version => version.Version)
                .ToList();
        }

        private static ProgressChapterModel? FindProgressChapter(ProgressModel? progress, string folder, int index)
        {
            if (progress is null)
            {
                return null;
            }

            var number = index.ToString(CultureInfo.InvariantCulture);
            return progress.Chapters.FirstOrDefault(chapter =>
                       string.Equals(chapter.ChapterNumber, folder, StringComparison.OrdinalIgnoreCase))
                   ?? progress.Chapters.FirstOrDefault(chapter =>
                       string.Equals(chapter.ChapterNumber, number, StringComparison.OrdinalIgnoreCase));
        }

        private static T? ReadJson<T>(string path) where T : class
        {
            var text = ReadText(path);
            if (text is null)
            {
                return null;
            }

            try
            {
                return JsonSerializer.Deserialize<T>(text, JsonOptions);
            }
            catch (JsonException exception)
            {
                throw new InvalidDataException($"Could not parse {path}: {exception.Message}", exception);
            }
        }

        private static string? ReadText(string path) => File.Exists(path) ? File.ReadAllText(path) : null;

        /// <summary>
        /// Reads a stage output folder, preferring <c>segment.md</c> but accepting other names
        /// used by older workspaces (for example <c>writer/prose.md</c>).
        /// </summary>
        private static string? ReadStageText(string directory)
        {
            var text = ReadText(Path.Combine(directory, "segment.md"));
            if (text is not null || !Directory.Exists(directory))
            {
                return text;
            }

            return Directory.GetFiles(directory, "*.md")
                .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                .Select(ReadText)
                .FirstOrDefault(candidate => !string.IsNullOrWhiteSpace(candidate));
        }

        private static int ParseIndex(string? name) =>
            int.TryParse(name, NumberStyles.Integer, CultureInfo.InvariantCulture, out var index) ? index : 0;

        private static int ParseVersion(string fileName)
        {
            var match = Regex.Match(fileName, @"_v(\d+)$", RegexOptions.IgnoreCase);
            return match.Success && int.TryParse(match.Groups[1].Value, CultureInfo.InvariantCulture, out var version)
                ? version
                : 0;
        }

        private static int NumericOrder(string name) =>
            int.TryParse(name, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value) ? value : int.MaxValue;

        private static string? FirstNonEmpty(params string?[] values) =>
            values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value));

        private static int CountWords(string? text) =>
            string.IsNullOrWhiteSpace(text)
                ? 0
                : text.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).Length;
    }
}
