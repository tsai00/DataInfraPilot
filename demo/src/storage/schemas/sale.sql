CREATE TABLE public.sale (
	id BIGSERIAL PRIMARY key,
	internal_id text,
	url text,
	disposition text NULL,
	"name" text NULL,
	area int8 NULL,
	price int8 NULL,
	region text NULL,
	city text NULL,
	city_part text NULL,
	street text NULL,
	lat float8 NULL,
	lon float8 NULL,
	_scraped_at TIMESTAMP WITH TIME ZONE,
	_data_source text
);