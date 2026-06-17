import CapabilityDetailV2 from "./CapabilityDetailV2";

export default function CapabilityDetailPage({
  params,
}: {
  params: { name: string };
}) {
  return <CapabilityDetailV2 params={params} />;
}
