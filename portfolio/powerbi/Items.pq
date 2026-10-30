let
    Source = Csv.Document(File.Contents(DataFolder & "Items.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"order_id", type text}, {"order_item_id", Int64.Type}, {"seller_id", type text}, {"product_id", type text}, {"price", Currency.Type}, {"freight_value", Currency.Type}}, "en-US")
in
    Typed
