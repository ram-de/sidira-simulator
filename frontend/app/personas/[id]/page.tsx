import PersonaPackDetailV2 from "./PersonaPackDetailV2";

export default function PersonaPackDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <PersonaPackDetailV2 params={params} />;
}
