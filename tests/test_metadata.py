import numpy as np
from xarray import DataArray
from xarray_multiscale.reducers import windowed_mean
from fibsem_tools.metadata.neuroglancer import (
    NeuroglancerN5GroupMetadata,
    PixelResolution,
)
from fibsem_tools.metadata.cosem import COSEMGroupMetadata, MultiscaleMeta, ScaleMeta
from fibsem_tools.metadata.transform import SpatialTransform
from xarray_multiscale import multiscale


def test_SpatialTransform():
    coords = [
        DataArray(np.arange(10), dims=("z"), attrs={"units": "nm"}),
        DataArray(np.arange(10) + 5, dims=("y",), attrs={"units": "m"}),
        DataArray(10 + (np.arange(10) * 10), dims=("x",), attrs={"units": "km"}),
    ]

    data = DataArray(np.zeros((10, 10, 10)), coords=coords)
    transform = SpatialTransform.fromDataArray(data)
    assert transform == SpatialTransform(
        axes=["z", "y", "x"],
        units=["nm", "m", "km"],
        translate=[0.0, 5.0, 10.0],
        scale=[1.0, 1.0, 10.0],
    )

    transform = SpatialTransform.fromDataArray(data, reverse_axes=True)
    assert transform == SpatialTransform(
        axes=["x", "y", "z"],
        units=["km", "m", "nm"],
        translate=[10.0, 5.0, 0.0],
        scale=[10.0, 1.0, 1.0],
    )


def test_neuroglancer_metadata():
    coords = [
        DataArray(np.arange(16) + 0.5, dims=("z"), attrs={"units": "nm"}),
        DataArray(np.arange(16) + 1 / 3, dims=("y",), attrs={"units": "m"}),
        DataArray(10 + (np.arange(16) * 100.1), dims=("x",), attrs={"units": "km"}),
    ]

    data = DataArray(np.zeros((16, 16, 16)), coords=coords)
    multi = multiscale(data, windowed_mean, (2, 2, 2))[:4]
    neuroglancer_metadata = NeuroglancerN5GroupMetadata.fromDataArrays(multi)

    assert neuroglancer_metadata == NeuroglancerN5GroupMetadata(
        axes=["x", "y", "z"],
        units=["km", "m", "nm"],
        scales=[[1, 1, 1], [2, 2, 2], [4, 4, 4], [8, 8, 8]],
        pixelResolution=PixelResolution(dimensions=[100.1, 1.0, 1.0], unit="km"),
    )


def test_cosem_ome():
    transform_base = {
        "axes": ["z", "y", "x"],
        "units": ["nm", "m", "km"],
        "translate": [0, -8, 10],
        "scale": [1.0, 1.0, 10.0],
    }
    shape_base = (16, 16, 16)
    coords = [
        DataArray(
            (np.arange(shape_base[idx]) * transform_base["scale"][idx])
            + transform_base["translate"][idx],
            dims=(transform_base["axes"][idx],),
            attrs={"units": transform_base["units"][idx]},
        )
        for idx in range(len(shape_base))
    ]

    data = DataArray(np.zeros(shape_base), coords=coords, name="data")
    multi = multiscale(data, windowed_mean, (2, 2, 2))[:2]
    paths = ["s0", "s1"]
    cosem_ome_group_metadata = COSEMGroupMetadata.fromDataArrays(
        multi, paths=paths, name="data"
    )
    scale_metas = [
        ScaleMeta(path=p, transform=SpatialTransform.fromDataArray(m))
        for p, m in zip(paths, multi)
    ]
    assert cosem_ome_group_metadata == COSEMGroupMetadata(
        multiscales=[MultiscaleMeta(name="data", datasets=scale_metas)]
    )
