export type SiteSettings = {
  company_name: string;
  tagline: string | null;
  about_short: string | null;
  phone_primary: string | null;
  phone_secondary: string | null;
  email_sales: string | null;
  whatsapp_number: string | null;
  address_line: string | null;
  city: string | null;
  google_maps_url: string | null;
  business_hours: string | null;
  facebook_url: string | null;
  linkedin_url: string | null;
  instagram_url: string | null;
  default_meta_title: string | null;
  default_meta_description: string | null;
};

export type CategoryRef = { id: number; name: string; slug: string };
export type SeriesRef = { name: string; slug: string };

export type ProductCardData = {
  id: number;
  name: string;
  slug: string;
  model_code: string | null;
  summary: string | null;
  is_featured: boolean;
  category: CategoryRef;
  series: SeriesRef;
  image: unknown; // shape unknown until we upload one
};

export type Industry = {
  id: number;
  name: string;
  slug: string;
  summary: string | null;
  description: string | null;
  icon: string | null;
};

export type SectionItem = { title: string; text: string; icon: string | null };

export type HomepageSection = {
  key: string;
  heading: string;
  subheading: string | null;
  cta_label: string | null;
  cta_url: string | null;
  image: unknown;
  items: SectionItem[];
  categories: unknown[]; // shape unknown until a featured category exists
  products: ProductCardData[];
  industries: Industry[];
};

export type HomepageResponse = { sections: HomepageSection[] };

export type ProductList = {
  items: ProductCardData[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type Category = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  product_count: number;
  children: Category[];
};

export type FacetOption = { value: string; count: number };

export type AttributeFacet = {
  key: string;
  label: string;
  unit: string | null;
  data_type: string; // "single_choice" or "multi_choice" so far
  options: FacetOption[];
};

export type SeriesFacet = { name: string; slug: string; count: number };

export type Facets = {
  total: number;
  series: SeriesFacet[];
  attributes: AttributeFacet[];
};

export type Specification = {
  key: string;
  label: string;
  group_name: string | null;
  unit: string | null;
  data_type: string;
  is_inquiry_option: boolean; // true for specs the visitor picks when asking for a quote
  value: string | string[];
};

export type ProductDetail = {
  id: number;
  name: string;
  slug: string;
  model_code: string | null;
  summary: string | null;
  description: string | null;
  is_featured: boolean;
  seo_title: string | null;
  seo_description: string | null;
  category: CategoryRef;
  parent_category: CategoryRef | null;
  brand: { name: string; slug: string } | null;
  series: SeriesRef | null;
  features: string[];
  applications: unknown[]; // shape unknown until one exists
  specifications: Specification[];
  industries: unknown[]; // shape unknown until one is linked
  related: ProductCardData[];
  images: unknown[]; // shape unknown until one is uploaded
};