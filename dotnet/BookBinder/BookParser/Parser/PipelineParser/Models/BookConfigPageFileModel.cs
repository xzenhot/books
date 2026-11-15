using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// One file of a page folder as the pipeline records it in <c>config.json</c>:
/// <c>{"order": 1, "file_path": "pages/cover/front.jpg"}</c>. The order is what the book prints by.
/// </summary>
[JsonConverter(typeof(PageFileConverter))]
public sealed class BookConfigPageFileModel
{
    /// <summary>Position of the file inside its page folder; kept as text because the pipeline writes it as either.</summary>
    [JsonPropertyName("order")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? Order { get; set; }

    [JsonPropertyName("file_path")]
    public string? FilePath { get; set; }
}

/// <summary>
/// Reads a page file written either as the bare path older files carry - <c>"pages/cover/front.jpg"</c> -
/// or as the ordered object the schema asks for, and always writes the object.
/// </summary>
public sealed class PageFileConverter : JsonConverter<BookConfigPageFileModel>
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

        writer.WriteEndObject();
    }
}
