using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// The authoritative book plan stored in <c>book.json</c>.
/// </summary>
public sealed class BookModel
{
    [JsonPropertyName("book_name")]
    public string? BookName { get; set; }

    [JsonPropertyName("book_long_title")]
    public string? BookLongTitle { get; set; }

    [JsonPropertyName("generic")]
    public string? Generic { get; set; }

    [JsonPropertyName("era")]
    public string? Era { get; set; }

    [JsonPropertyName("language")]
    public string? Language { get; set; }

    [JsonPropertyName("target_audience")]
    public string? TargetAudience { get; set; }

    [JsonPropertyName("chapter_count")]
    public int ChapterCount { get; set; }

    [JsonPropertyName("segment_count")]
    public int? SegmentCount { get; set; }

    [JsonPropertyName("factory")]
    public string? Factory { get; set; }

    [JsonPropertyName("form")]
    public string? Form { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("style")]
    public string? Style { get; set; }

    [JsonPropertyName("provider")]
    public string? Provider { get; set; }

    [JsonPropertyName("book_summary")]
    public string? BookSummary { get; set; }

    // Plans in the wild mix ISO timestamps, date-only values, and free text such as "today".
    [JsonPropertyName("created_at")]
    public string? CreatedAt { get; set; }

    [JsonPropertyName("updated_at")]
    public string? UpdatedAt { get; set; }

    [JsonPropertyName("updated_date")]
    public string? UpdatedDate { get; set; }

    [JsonPropertyName("updated_by")]
    public string? UpdatedBy { get; set; }

    [JsonPropertyName("user_name")]
    public string? UserName { get; set; }

    [JsonPropertyName("gist")]
    public string? Gist { get; set; }

    [JsonPropertyName("word_target")]
    public int WordTarget { get; set; }

    [JsonPropertyName("register")]
    public string? Register { get; set; }

    [JsonPropertyName("quality")]
    public string? Quality { get; set; }

    [JsonPropertyName("themes")]
    public List<string> Themes { get; set; } = [];

    [JsonPropertyName("reference")]
    public string? Reference { get; set; }

    [JsonPropertyName("index")]
    public string? Index { get; set; }

    [JsonPropertyName("sacred_vocabulary")]
    public List<string> SacredVocabulary { get; set; } = [];

    [JsonPropertyName("translation_guide")]
    public string? TranslationGuide { get; set; }

    [JsonPropertyName("all_characters")]
    public List<CharacterModel> AllCharacters { get; set; } = [];

    [JsonPropertyName("filter_chain")]
    [JsonConverter(typeof(ChainItemListConverter))]
    public List<ChainItemModel> FilterChain { get; set; } = [];

    [JsonPropertyName("quality_chain")]
    [JsonConverter(typeof(ChainItemListConverter))]
    public List<ChainItemModel> QualityChain { get; set; } = [];

    [JsonPropertyName("chapters")]
    public List<ChapterModel> Chapters { get; set; } = [];

    [JsonPropertyName("source_terms")]
    public List<string> SourceTerms { get; set; } = [];

    [JsonPropertyName("signature")]
    public string? Signature { get; set; }

    /// <summary>Fields not modeled here (for example novel-only keys) are preserved on round-trip.</summary>
    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
