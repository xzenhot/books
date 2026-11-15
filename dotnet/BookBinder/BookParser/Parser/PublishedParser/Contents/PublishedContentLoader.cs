using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;

using WriterWorker.Parser.PipelineParser.Contents;
using WriterWorker.Parser.PipelineParser.Models;
using WriterWorker.Parser.PublishedParser.Models;

namespace WriterWorker.Parser.PublishedParser.Contents
{
    /// <summary>
    /// Fills a <see cref="BookContent"/> from one published version folder, for example
    /// <c>...\writer\workspaces\published\nouka\version6</c>:
    /// <list type="bullet">
    /// <item><c>manifest.json</c> for the publication date and the chapter order.</item>
    /// <item><c>book.md</c> for the book title and the publish stamps.</item>
    /// <item><c>chapters/{n}/chapter.json</c> + <c>chapter.md</c>.</item>
    /// <item><c>chapters/{n}/segments/{i}/{editor,latest}/segment.md</c>.</item>
    /// </list>
    /// The result is the same <see cref="BookContent"/> the pipeline parser produces, so the render
    /// model converter and the PDF export work with a published edition unchanged. Missing files are
    /// skipped, so a partial version still loads.
    /// </summary>
    public static class PublishedContentLoader
    {
        /// <summary>State and status reported for everything read out of a published version.</summary>
        public const string PublishedState = "published";

        private static readonly JsonSerializerOptions JsonOptions = new()
        {
            PropertyNameCaseInsensitive = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };

        /// <summary>Reads a published version folder.</summary>
        /// <param name="versionFolder">The version folder, for example <c>...\published\nouka\version6</c>.</param>
        /// <param name="plan">
        /// Plan of the same book in the pipeline (<c>book.json</c>), when the caller has one. Published
        /// versions only record the publishing agent, so a plan supplies the language, form and author.
        /// </param>
        public static BookContent Load(string versionFolder, BookModel? plan = null)
        {
            var content = new BookContent();
            Fill(content, versionFolder, plan);
            return content;
        }

        /// <summary>Reads a published version folder into an existing content object.</summary>
        public static void Fill(BookContent content, string versionFolder, BookModel? plan = null)
        {
            ArgumentNullException.ThrowIfNull(content);

            if (string.IsNullOrWhiteSpace(versionFolder))
            {
                throw new ArgumentException("A published version folder is required.", nameof(versionFolder));
            }

            var root = Path.GetFullPath(versionFolder);
            if (!Directory.Exists(root))
            {
                throw new DirectoryNotFoundException($"Published version folder not found: {root}");
            }

            var chaptersDirectory = Path.Combine(root, "chapters");
            if (!File.Exists(Path.Combine(root, "manifest.json"))
                && !File.Exists(Path.Combine(root, "book.md"))
                && !Directory.Exists(chaptersDirectory))
            {
                throw new InvalidOperationException(
                    $"Not a published version folder (no manifest.json, book.md or chapters): {root}");
            }

            var manifest = ReadJson<PublishedManifestModel>(Path.Combine(root, "manifest.json"));
            PublishedMarkdown.Read(ReadText(Path.Combine(root, "book.md")), out var title);

            content.WorkspacePath = root;
            content.Plan = plan ?? BuildPlan(root, manifest, title);

            content.Chapters.Clear();
            content.Documents.Clear();
            foreach (var chapter in LoadChapters(root, chaptersDirectory, manifest, content.Plan))
            {
                content.Chapters.Add(chapter);
            }

            content.Progress = BuildProgress(root, manifest, content.Plan, title, content.Chapters);
        }

        /// <summary>
        /// The published tree has no <c>book.json</c>, so the plan is rebuilt from the manifest, the
        /// <c>book.md</c> heading and the book folder name.
        /// </summary>
        private static BookModel BuildPlan(string root, PublishedManifestModel? manifest, string? title)
        {
            var bookName = BookFolderName(root);
            return new BookModel
            {
                BookName = bookName,
                BookLongTitle = FirstNonEmpty(title, bookName),
                ChapterCount = manifest?.Chapters.Count ?? 0,
                UpdatedBy = manifest?.UpdatedBy,
                UpdatedDate = manifest?.PublishedAt ?? manifest?.UpdatedDate,
                CreatedAt = manifest?.PublishedAt ?? manifest?.UpdatedDate,
            };
        }

        /// <summary>
        /// Mirrors what <c>progress.json</c> reports for a published book: the version number, the
        /// publication date and every chapter marked as published.
        /// </summary>
        private static ProgressModel BuildProgress(
            string root,
            PublishedManifestModel? manifest,
            BookModel? plan,
            string? title,
            List<ChapterContent> chapters)
        {
            var version = PublishedVersion.ParseNumber(Path.GetFileName(
                root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)));

            var progress = new ProgressModel
            {
                Title = title ?? plan?.BookLongTitle,
                BookName = plan?.BookName ?? BookFolderName(root),
                Language = plan?.Language,
                Form = plan?.Form,
                TotalChapters = chapters.Count,
                CompletedChapters = chapters.Count,
                WrittenChapters = chapters.Count,
                Published = true,
                PublishedAt = manifest?.PublishedAt ?? manifest?.UpdatedDate,
                PublishedVersion = version > 0 ? version : null,
                UpdatedBy = manifest?.UpdatedBy,
                UpdatedDate = manifest?.UpdatedDate,
            };

            foreach (var chapter in chapters)
            {
                progress.Chapters.Add(new ProgressChapterModel
                {
                    ChapterNumber = chapter.Name,
                    Topic = chapter.Title,
                    Status = PublishedState,
                    FilePath = chapter.FilePath,
                    CompletedDate = chapter.CreatedOn,
                    Written = true,
                    Validated = true,
                    Published = true,
                    PublishedVersion = progress.PublishedVersion,
                    PublishedSha256 = FindSha256(manifest, chapter.Name),
                });
            }

            return progress;
        }

        private static string? FindSha256(PublishedManifestModel? manifest, string name) =>
            manifest?.Chapters.FirstOrDefault(chapter =>
                string.Equals(chapter.Name, name, StringComparison.OrdinalIgnoreCase))?.Sha256;

        private static IEnumerable<ChapterContent> LoadChapters(
            string root,
            string chaptersDirectory,
            PublishedManifestModel? manifest,
            BookModel? plan)
        {
            if (!Directory.Exists(chaptersDirectory))
            {
                return [];
            }

            var author = FirstNonEmpty(plan?.UserName, plan?.UpdatedBy);
            return OrderChapterDirectories(chaptersDirectory, manifest)
                .Select(directory => LoadChapter(directory, author))
                .ToList();
        }

        /// <summary>manifest.json lists the chapters in publication order, which is the reading order.</summary>
        private static List<string> OrderChapterDirectories(string chaptersDirectory, PublishedManifestModel? manifest)
        {
            var directories = Directory.GetDirectories(chaptersDirectory)
                .OrderBy(directory => NumericOrder(Path.GetFileName(directory)))
                .ThenBy(directory => Path.GetFileName(directory), StringComparer.OrdinalIgnoreCase)
                .ToList();

            if (manifest is null || manifest.Chapters.Count == 0)
            {
                return directories;
            }

            var order = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            for (var position = 0; position < manifest.Chapters.Count; position++)
            {
                var name = manifest.Chapters[position].Name;
                if (!string.IsNullOrWhiteSpace(name))
                {
                    order.TryAdd(name, position);
                }
            }

            return directories
                .OrderBy(directory => order.TryGetValue(Path.GetFileName(directory), out var position) ? position : int.MaxValue)
                .ThenBy(directory => NumericOrder(Path.GetFileName(directory)))
                .ThenBy(directory => Path.GetFileName(directory), StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static ChapterContent LoadChapter(string directory, string? author)
        {
            var folder = Path.GetFileName(directory);
            var chapterFile = ReadJson<ChapterFileModel>(Path.Combine(directory, "chapter.json"));
            var markdownPath = Path.Combine(directory, "chapter.md");
            var markdown = PublishedMarkdown.Read(ReadText(markdownPath), out var heading);

            var chapter = new ChapterContent
            {
                Directory = directory,
                Index = chapterFile?.ChapterIndex ?? ParseIndex(folder),
                Name = FirstNonEmpty(chapterFile?.Name, folder) ?? folder,
                Title = FirstNonEmpty(chapterFile?.ChapterTitle, heading),
                Summary = chapterFile?.ChapterSummary,
                State = PublishedState,
                Status = PublishedState,
                CompletedDate = chapterFile?.UpdatedDate,
                CreatedBy = FirstNonEmpty(chapterFile?.UpdatedBy, author),
                CreatedOn = chapterFile?.UpdatedDate,
                FilePath = File.Exists(markdownPath) ? markdownPath : null,
                WordTarget = chapterFile?.WordTarget ?? 0,
                Markdown = markdown,
            };

            chapter.FurtherReferences.AddRange(chapterFile?.FurtherReferences ?? []);
            foreach (var segment in LoadSegments(directory, chapterFile, chapter.CreatedBy, chapter.CreatedOn))
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
            string? author,
            string? createdOn)
        {
            var segmentsDirectory = Path.Combine(chapterDirectory, "segments");
            if (!Directory.Exists(segmentsDirectory))
            {
                return MetadataOnlySegments(chapterFile, author, createdOn);
            }

            return Directory.GetDirectories(segmentsDirectory)
                .OrderBy(directory => NumericOrder(Path.GetFileName(directory)))
                .ThenBy(directory => Path.GetFileName(directory), StringComparer.OrdinalIgnoreCase)
                .Select(directory => LoadSegment(directory, chapterFile, author, createdOn))
                .ToList();
        }

        private static SegmentContent LoadSegment(
            string directory,
            ChapterFileModel? chapterFile,
            string? author,
            string? createdOn)
        {
            var folder = Path.GetFileName(directory);
            var segmentFile = ReadJson<SegmentFileModel>(Path.Combine(directory, "segment.json"));
            var index = segmentFile?.SegmentIndex ?? ParseIndex(folder);

            // A published version has no segment.json: the titles live in the chapter file.
            var metadata = segmentFile
                ?? chapterFile?.Segments.FirstOrDefault(segment => segment.SegmentIndex == index)
                ?? chapterFile?.Segments.FirstOrDefault(segment =>
                    string.Equals(segment.Name, folder, StringComparison.OrdinalIgnoreCase));

            var segment = new SegmentContent
            {
                Directory = directory,
                Index = index,
                Name = FirstNonEmpty(metadata?.Name, folder) ?? folder,
                Title = metadata?.SegmentTitle,
                Summary = metadata?.SegmentSummary,
                State = PublishedState,
                CreatedBy = author,
                CreatedOn = createdOn,
                WordTarget = metadata?.WordTarget ?? 0,
                LatestText = ReadStageText(directory, "latest"),
                EditorText = ReadStageText(directory, "editor"),
                SegmentText = ReadStampedText(Path.Combine(directory, "segment.md")),
                WriterText = ReadStageText(directory, "writer"),
                TranslatedText = ReadStageText(directory, "translator"),
            };

            segment.FurtherReferences.AddRange(metadata?.FurtherReferences ?? []);
            segment.WordCount = CountWords(segment.Text);
            return segment;
        }

        private static IEnumerable<SegmentContent> MetadataOnlySegments(
            ChapterFileModel? chapterFile,
            string? author,
            string? createdOn)
        {
            if (chapterFile?.Segments is not { Count: > 0 } fileSegments)
            {
                return [];
            }

            return fileSegments
                .Select(segment => new SegmentContent
                {
                    Index = segment.SegmentIndex ?? ParseIndex(segment.Name),
                    Name = segment.Name ?? string.Empty,
                    Title = segment.SegmentTitle,
                    Summary = segment.SegmentSummary,
                    State = PublishedState,
                    CreatedBy = author,
                    CreatedOn = createdOn,
                    WordTarget = segment.WordTarget ?? 0,
                })
                .ToList();
        }

        /// <summary>
        /// Reads a stage folder (<c>segments/{i}/latest</c>), preferring <c>segment.md</c> and
        /// accepting any other markdown name the workspaces use.
        /// </summary>
        private static string? ReadStageText(string directory, string stage)
        {
            var stageDirectory = Path.Combine(directory, stage);
            var text = ReadStampedText(Path.Combine(stageDirectory, "segment.md"));
            if (text is not null || !Directory.Exists(stageDirectory))
            {
                return text;
            }

            return Directory.GetFiles(stageDirectory, "*.md")
                .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                .Select(ReadStampedText)
                .FirstOrDefault(candidate => !string.IsNullOrWhiteSpace(candidate));
        }

        /// <summary>Reads a markdown file and drops the provenance block the publish step added.</summary>
        private static string? ReadStampedText(string path)
        {
            var text = ReadText(path);
            return text is null ? null : PublishedMarkdown.Read(text, out _);
        }

        private static string BookFolderName(string versionFolder)
        {
            var bookFolder = Directory.GetParent(
                versionFolder.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
            var name = bookFolder?.Name;
            return string.IsNullOrWhiteSpace(name) ? versionFolder : name;
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

        private static int ParseIndex(string? name) =>
            int.TryParse(name, NumberStyles.Integer, CultureInfo.InvariantCulture, out var index) ? index : 0;

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
