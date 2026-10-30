let
    Source = Csv.Document(File.Contents(DataFolder & "Products.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"product_id", type text}, {"category", type text}}, "en-US")
in
    Typed
