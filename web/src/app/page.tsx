import { getHomepage } from "@/lib/homepage";
import { SectionRenderer } from "@/components/home-sections";

export default async function Home() {
  const { sections } = await getHomepage();
  return (
    <>
      {sections.map((section) => (
        <SectionRenderer key={section.key} section={section} />
      ))}
    </>
  );
}