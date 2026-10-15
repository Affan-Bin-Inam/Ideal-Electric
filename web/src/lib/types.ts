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