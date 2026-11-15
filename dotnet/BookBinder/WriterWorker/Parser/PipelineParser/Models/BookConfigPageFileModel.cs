using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// One file of a page folder as the profile records it in <c>profile.json</c>:
/// <c>{"order": 1, "file_path": "pages/cover/front.jpg", "content_type": "image/jpeg"}</c>. The order
/// is what the book prints by and the content type is what the page is printed as - the
/// <c>format</c> of the folder is only the preference a page without a type of its own falls back on.
/// </summary>
[JsonConverter(typeof(PageFileConverter))]
internal sealed class BookConfigPageFileModel
{
    /// <summary>Position of the file inside its page folder; kept as text because the pipeline writes it as either.</summary>
    [JsonPropertyName("order")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? Order { get; set; }

    [JsonPropertyName("file_path")]
    public string? FilePath { get; set; }

    /// <summary>
    /// Kind of the file as its MIME type - <c>application/rtf</c>, <c>text/markdown</c>,
    /// <c>image/jpeg</c>. It decides how the page prints, so a page keeps its kind even when the
    /// folder it sits in is set up for another one.
    /// </summary>
    [JsonPropertyName("content_type")]
    public string? ContentType { get; set; }
}

/// <summary>
/// Reads a page file written either as the bare path older files carry - <c>"pages/cover/front.jpg"</c> -
/// or as the ordered object the schema asks for, and always writes the object.
/// </summary>
internal sealed class PageFileConverter : JsonConverter<BookConfigPageFileModel>
{
    public override BookConfigPageFileModel? Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType == JsonTokenType.String)
        {
            return new BookConfigPageFileModel { FilePath = reader.GetString() };
        }

        if (reader.TokenType == JsonTokenType.Null)
        {
            return null;
        }

        if (reader.TokenType != JsonTokenType.StartObject)
        {
            throw new JsonException($"Expected a page file path or object but found {reader.TokenType}.");
        }

        var file = new BookConfigPageFileModel();

        while (reader.Read())
        {
            switch (reader.TokenType)
            {
                case JsonTokenType.EndObject:
                    return file;

                case JsonTokenType.PropertyName:
                    var property = reader.GetString();
                    reader.Read();

                    switch (property)
                    {
                        case "order":
                            file.Order = reader.TokenType switch
                            {
                                JsonTokenType.Number => reader.TryGetInt64(out var number)
                                    ? number.ToString(CultureInfo.InvariantCulture)
                                    : reader.GetDouble().ToString(CultureInfo.InvariantCulture),
                                JsonTokenType.String => reader.GetString(),
                                JsonTokenType.Null => null,
                                _ => throw new JsonException($"Expected an order but found {reader.TokenType}.")
                            };
                            break;

                        case "file_path":
                            file.FilePath = reader.TokenType == JsonTokenType.Null ? null : reader.GetString();
                            break;

                        case "content_type":
                            file.ContentType = reader.TokenType == JsonTokenType.Null ? null : reader.GetString();
                            break;

                        default:
                            reader.Skip();
                            break;
                    }

                    break;
            }
        }

        throw new JsonException("The page file object was not closed.");
    }

    public override void Write(Utf8JsonWriter writer, BookConfigPageFileModel value, JsonSerializerOptions options)
    {
        writer.WriteStartObject();

        if (long.TryParse(value.Order, NumberStyles.None, CultureInfo.InvariantCulture, out var order))
        {
            writer.WriteNumber("order", order);
        }
        else if (!string.IsNullOrWhiteSpace(value.Order))
        {
            writer.WriteString("order", value.Order);
        }

        if (value.FilePath is { } path)
        {
            writer.WriteString("file_path", path);
        }

        if (!string.IsNullOrWhiteSpace(value.ContentType))
        {
            writer.WriteString("content_type", value.ContentType.Trim());
        }

        writer.WriteEndObject();
    }
}
