using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PublishedParser.Models;

/// <summary>
/// The manifest of one published version (<c>version{n}/manifest.json</c>): when the version was
/// cut and the hash of every chapter it holds, in publication order.
/// </summary>
public sealed class PublishedManifestModel
{
    [JsonPropertyName("published_at")]
    public string? PublishedAt { get; set; }

    [JsonPropertyName("updated_by")]
    public string? UpdatedBy { get; set; }

    [JsonPropertyName("updated_date")]
    public string? UpdatedDate { get; set; }

    /// <summary>Published chapters in reading order; this is the authoritative chapter order.</summary>
    [JsonPropertyName("chapters")]
    public List<PublishedManifestChapterModel> Chapters { get; set; } = [];

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

/// <summary>One chapter of a published version together with the hash of the text it was cut from.</summary>
public sealed class PublishedManifestChapterModel
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("sha256")]
    public string? Sha256 { get; set; }
}
