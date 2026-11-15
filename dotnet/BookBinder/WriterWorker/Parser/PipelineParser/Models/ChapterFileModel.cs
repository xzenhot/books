using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// Per-chapter state file at <c>chapters/{n}/chapter.json</c>.
/// </summary>
internal sealed class ChapterFileModel
{
    [JsonPropertyName("chapter_index")]
    public int? ChapterIndex { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("word_target")]
    public int? WordTarget { get; set; }

    [JsonPropertyName("segment_count")]
    public int? SegmentCount { get; set; }

    [JsonPropertyName("chapter_title")]
    public string? ChapterTitle { get; set; }

    [JsonPropertyName("chapter_summary")]
    public string? ChapterSummary { get; set; }

    [JsonPropertyName("level")]
    public string? Level { get; set; }

    [JsonPropertyName("state")]
    public string? State { get; set; }

    [JsonPropertyName("further_references")]
    public List<FurtherReferenceModel> FurtherReferences { get; set; } = [];

    /// <summary>Either full segment objects or bare segment numbers, depending on the workspace.</summary>
    [JsonPropertyName("segments")]
    [JsonConverter(typeof(SegmentFileListConverter))]
    public List<SegmentFileModel> Segments { get; set; } = [];

    // Published chapter.json files carry the publish stamp.
    [JsonPropertyName("updated_by")]
    public string? UpdatedBy { get; set; }

    [JsonPropertyName("updated_date")]
    public string? UpdatedDate { get; set; }

    [JsonPropertyName("draft")]
    public ChapterDraftModel? Draft { get; set; }

    [JsonPropertyName("quality_review")]
    public ChapterQualityReviewModel? QualityReview { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

internal sealed class ChapterDraftModel
{
    [JsonPropertyName("sha256")]
    public string? Sha256 { get; set; }

    [JsonPropertyName("written_at")]
    public string? WrittenAt { get; set; }

    [JsonPropertyName("origin")]
    public string? Origin { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

internal sealed class ChapterQualityReviewModel
{
    [JsonPropertyName("status")]
    public string? Status { get; set; }

    [JsonPropertyName("sha256")]
    public string? Sha256 { get; set; }

    [JsonPropertyName("reviewer")]
    public string? Reviewer { get; set; }

    [JsonPropertyName("reviewed_at")]
    public string? ReviewedAt { get; set; }

    /// <summary>Free-form audit notes; workspaces write them as a list of strings.</summary>
    [JsonPropertyName("notes")]
    public List<string> Notes { get; set; } = [];

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
