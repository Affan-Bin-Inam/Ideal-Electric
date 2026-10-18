// What /api/v1/auth/me returns. I only rely on these three fields.
export type AdminUser = { id: number; email: string; full_name: string; role: string };

export type AdminSiteSettings = {
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
  is_placeholder: boolean;
  updated_at: string;
};

export const INQUIRY_STATUSES = ["new", "contacted", "quoted", "closed", "spam"] as const;

export type InquiryListItem = {
  id: number;
  name: string;
  phone: string | null;
  company: string | null;
  product_name: string | null;
  status: string;
  assigned_to_email: string | null;
  created_at: string;
};

export type InquiryListData = {
  items: InquiryListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

// A guess until a real note exists: send me one and I'll tighten this.
export type InquiryNote = {
  id: number;
  author_email: string | null;
  body: string;
  created_at: string;
};

export type InquiryDetailData = {
  id: number;
  name: string;
  company: string | null;
  email: string | null;
  phone: string | null;
  whatsapp_url: string | null;
  city: string | null;
  message: string | null;
  product_id: number | null;
  product_name: string | null;
  selected_options: Record<string, string[]> | null;
  source_page: string | null;
  status: string;
  assigned_to_id: number | null;
  assigned_to_email: string | null;
  created_at: string;
  updated_at: string;
  notes: InquiryNote[];
};