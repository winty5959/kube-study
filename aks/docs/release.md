# AKS release promotion

AKS release tags use `aks-vMAJOR.MINOR.PATCH`. The tag workflow reads the four
CI-published development image tags (`api`, `worker`, `frontend`, and `minio`),
checks each registry manifest, creates release aliases from those immutable
digests without rebuilding, and opens a PR that changes only
`aks/k8s/overlays/prod/kustomization.yaml`.

Before creating a release tag, confirm the current `main` development image
tags were published successfully and run:

```sh
python3 aks/scripts/prepare-release.py --release aks-v1.0.0 --dry-run
pytest aks/scripts/tests/test_release.py aks/scripts/tests/test_image_tags.py
```

The dry run must leave the prod overlay unchanged. The workflow refuses a
development tag that is not in the `sha-<7 lowercase hex>` form and refuses to
overwrite an existing release alias when its manifest digest differs.

## Production sync boundary

`root-prod` is manually synced to create the prod child Applications. The
`credentials-prod` app applies the strict-scope `album-prod` SealedSecret and
namespace. `platform-prod` owns the prod Postgres, Redis, and MinIO workloads;
it is manually synced so creating the release aliases cannot update MinIO
ahead of the application release. The cluster-wide KEDA, Sealed Secrets,
ingress, monitoring, and observability installations remain owned by dev and
are not installed again for prod.

After reviewing and merging a release PR, manually sync `platform-prod` first
and wait for its three PVCs and data services to become Ready. Then manually
sync `album-prod`. Its PostSync smoke check verifies upload, thumbnail
generation, original download, and delete. Compare all four running image
manifest digests with the release PR's verified digest table. The prod host is
`album.aks.prod.localhost`.

Prod album credentials are generated separately from dev at
`~/.local/share/kube-study/aks-prod-secrets.env`. The local plaintext file and
AKS Sealed Secrets private key backup stay outside Git; only strict-scope
ciphertext is committed. The shared Grafana credential remains managed once
in the `monitoring` namespace.
