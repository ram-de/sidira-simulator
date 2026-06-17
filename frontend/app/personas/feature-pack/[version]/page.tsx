import FeaturePackV2 from "./FeaturePackV2";

export default function FeaturePackPage({
  params,
}: {
  params: { version: string };
}) {
  return <FeaturePackV2 params={params} />;
}
