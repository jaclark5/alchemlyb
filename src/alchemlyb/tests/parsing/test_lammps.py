"""LAMMPS parser tests.

"""

import copy
import pytest
from numpy.testing import assert_almost_equal

from alchemlyb.parsing import lammps as lmp
from alchemtest.lammps import load_benzene, load_lj_dimer

T_K = 300
pressure = 1.01325
kwargs_ti = {"column_lambda1": 1, "column_dlambda1": 2, "columns_derivative": [8, 7]}
kwargs_mbar = {
    "1_coul-off": {
        "indices": [2, 3],
        "ensemble": "npt",
        "prec": 3,
        "pressure": pressure,
    },
    "2_vdw": {
        "column_dU": 5,
        "column_U": 4,
        "indices": [2, 3],
        "ensemble": "npt",
        "prec": 3,
        "pressure": pressure,
        "column_volume": 7,
    },
    "3_coul-on": {
        "column_dU": 4,
        "column_U": 3,
        "indices": [2, 3],
        "prec": 3,
    },
}
kwargs_ti = {
    "1_coul-off": {
        "column_lambda1": 1,
        "column_dlambda1": 2,
        "columns_derivative": [8, 7],
    },
    "2_vdw": {"column_lambda1": 1, "column_dlambda1": 2, "columns_derivative": [9, 8]},
    "3_coul-on": {
        "column_lambda1": 1,
        "column_dlambda1": 2,
        "columns_derivative": [8, 7],
    },
}

T_lj = 0.7
P_lj = 0.01


def test_beta_from_units():
    """Test value of beta in different units."""

    assert_almost_equal(lmp.beta_from_units(T_K, "real"), 1.6774, decimal=4)
    assert_almost_equal(lmp.beta_from_units(T_lj, "lj"), 1.4286, decimal=4)
    assert_almost_equal(lmp.beta_from_units(T_K, "metal"), 38.6817, decimal=4)
    assert_almost_equal(lmp.beta_from_units(T_K, "si"), 2.414323505391137e20, decimal=4)
    assert_almost_equal(lmp.beta_from_units(T_K, "cgs"), 24143235053911.37, decimal=4)
    assert_almost_equal(lmp.beta_from_units(T_K, "electron"), 1052.5834, decimal=4)
    assert_almost_equal(lmp.beta_from_units(T_K, "micro"), 241432.3505, decimal=4)
    assert_almost_equal(lmp.beta_from_units(T_K, "nano"), 0.24143, decimal=4)


def test_energy_from_units():
    """Test value of beta in different units."""

    assert_almost_equal(lmp.energy_from_units("real"), 1.4584e-05, decimal=4)
    assert_almost_equal(lmp.energy_from_units("lj"), 1, decimal=4)
    assert_almost_equal(lmp.energy_from_units("metal"), 6.2415e-07, decimal=4)
    assert_almost_equal(lmp.energy_from_units("si"), 1, decimal=4)
    assert_almost_equal(lmp.energy_from_units("cgs"), 1, decimal=4)
    assert_almost_equal(
        lmp.energy_from_units("electron"), 3.3989309217431655e-14, decimal=4
    )
    assert_almost_equal(lmp.energy_from_units("micro"), 1, decimal=4)
    assert_almost_equal(lmp.energy_from_units("nano"), 1, decimal=4)


def test_u_nk():
    """Test that u_nk has the correct form when extracted from files."""
    dataset = load_benzene()

    for leg, filenames in dataset["data"]["mbar"].items():
        u_nk = lmp.extract_u_nk(filenames, 300, **kwargs_mbar[leg])

        assert u_nk.index.names == ["time", "fep-lambda"]
        if leg == "1_coul-off":
            assert u_nk.shape == (30006, 6)
        elif leg == "2_vdw":
            assert u_nk.shape == (78681, 16)
        elif leg == "3_coul-on":
            assert u_nk.shape == (30006, 6)
            assert u_nk.attrs["temperature"] == 300
            assert u_nk.attrs["energy_unit"] == "kT"


def test_u_nk_glob_error():
    """Test if files are not found."""
    with pytest.raises(
        ValueError,
        match=r"No files have been found that match: test_\*.txt",
    ):
        u_nk = lmp.extract_u_nk("test_*.txt", T=300)


def test_dHdl():
    """Test that dHdl has the correct form when extracted from files."""
    dataset = load_benzene()

    leg = "1_coul-off"
    dHdl = lmp.extract_dHdl(dataset["data"]["ti"][leg], T=300, **kwargs_ti[leg])

    assert dHdl.index.names == ["time", "fep-lambda"]
    assert dHdl.shape == (30006, 1)
    assert dHdl.attrs["temperature"] == 300
    assert dHdl.attrs["energy_unit"] == "kT"


def test_dHdl_glob_error():
    """Test if files are not found."""
    with pytest.raises(
        ValueError,
        match=r"No files have been found that match: test_\*.txt",
    ):
        u_nk = lmp.extract_dHdl("test_*.txt", T=300)


class TestLammpsMbar:

    @staticmethod
    @pytest.fixture(scope="class")
    def data():
        dataset = load_benzene()
        leg = "2_vdw"
        filenames = dataset["data"]["mbar"][leg]
        kwargs = kwargs_mbar[leg]
        filenames2 = load_benzene()["data"]["mbar"]["1_coul-off"]
        return filenames, kwargs, filenames2

    def test_u_nk_npt_error(
        self,
        data,
    ):
        """Test that initializing u_nk from NPT fails without pressure"""
        filenames, kwargs, _ = copy.deepcopy(data)
        del kwargs["pressure"]

        with pytest.raises(
            ValueError,
            match=r"In the npt ensemble, a pressure must be provided in the form of a positive float",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_unknown_ensemble(
        self,
        data,
    ):
        """Test that initializing u_nk that only known ensembles are accepted"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["ensemble"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Only ensembles of nvt or npt are supported.",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_nvt_with_pressure(
        self,
        data,
    ):
        """Test that initializing u_nk that only known ensembles are accepted"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["ensemble"] = "nvt"
        with pytest.raises(
            ValueError,
            match=r"There is no volume correction in the nvt ensemble, the pressure value will not be used.",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_wrong_cols(
        self,
        data,
    ):
        """Test length of columns"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["columns_lambda1"] = [1, 2, 2]
        with pytest.raises(
            ValueError,
            match=r"Provided columns for lambda1 must have a length of two, columns_lambda1: \[1, 2, 2\]",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_wrong_col_type(
        self,
        data,
    ):
        """Test columns_lambda type error"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["columns_lambda1"] = ["test", 2]
        with pytest.raises(
            ValueError,
            match=r"Provided column for columns_lambda1 must be type int. columns_lambda1: \['test', 2\]",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_col2_type_error(
        self,
        data,
    ):
        """Test column_lambda2 type error"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["column_lambda2"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for lambda must be type int. column_lambda2: test, type: <class 'str'>",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_col_dU_type_error(
        self,
        data,
    ):
        """Test column_dU type error"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["column_dU"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for dU_nk must be type int. column_dU: test, type: <class 'str'>",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_col_U_type_error(
        self,
        data,
    ):
        """Test column_U type error"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["column_U"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for U must be type int. column_U: test, type: <class 'str'>",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_col_lambda2_error(
        self,
        data,
    ):
        """Test that initializing u_nk that only known ensembles are accepted"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["column_lambda2"] = 3

        with pytest.raises(
            ValueError,
            match=r"If column_lambda2 is defined, the length of `indices` should be 3 indicating the value of the second value of lambda held constant.",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_col_lambda2(
        self,
        data,
    ):
        """Test that initializing u_nk that only known ensembles are accepted"""
        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["column_lambda2"] = 3
        kwargs["indices"].append(-1)
        u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)
        assert u_nk.index.names == ["time", "coul-lambda", "vdw-lambda"]

        kwargs["vdw_lambda"] = 2
        u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)
        assert u_nk.index.names == ["time", "coul-lambda", "vdw-lambda"]

        with pytest.raises(
            ValueError,
            match=r"vdw_lambda must be either 1 or 2, not: 3",
        ):
            kwargs["vdw_lambda"] = 3
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_no_file(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs, _ = copy.deepcopy(data)
        filenames.append("test_test_1_1_test_1.txt")

        with pytest.raises(
            ValueError,
            match=r"File not found: test_test_1_1_test_1.txt",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_inconsistent_lambda(self, data):
        """Test error no file"""

        filenames, kwargs, filenames2 = copy.deepcopy(data)
        filenames[:4] = filenames2[:4]

        with pytest.raises(
            ValueError,
            match=r"BAR calculation cannot be performed without the following lambda-lambda prime combinations: \[\(0.95, 1.0\)\]",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_nonfloat_lambda(self, data):
        """Test nonfloat lambda"""

        filenames, kwargs, filenames2 = copy.deepcopy(data)
        kwargs["indices"] = [1, 2]

        with pytest.raises(
            ValueError,
            match=r"Entry, 1 in filename cannot be converted to float: ",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

        kwargs["indices"] = [2, 1]

        with pytest.raises(
            ValueError,
            match=r"Entry, 1 in filename cannot be converted to float: ",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

        kwargs["indices"] = [2, 3, 1]

        with pytest.raises(
            ValueError,
            match=r"Entry, 1 in filename cannot be converted to float: ",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_multiple_values_lambda2(self, data):
        """Test multiple values of lambda"""

        filenames, kwargs, filenames2 = copy.deepcopy(data)
        kwargs["indices"] = [2, 3, 2]

        with pytest.raises(
            ValueError,
            match=r"More than one value of lambda2 is present in the provided files.",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_num_cols(self, data):
        """Test error no file"""

        filenames, kwargs, filenames2 = copy.deepcopy(data)
        ind1 = [i for i, x in enumerate(filenames) if "_1_1" in x][0]
        ind2 = [i for i, x in enumerate(filenames2) if "_1_1" in x][0]
        filenames[ind1] = filenames2[ind2]
        with pytest.raises(
            ValueError,
            match=r"Number of columns, 7, is less than necessary for indices: \[7\]",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_prec_1(self, data):
        """Test error no file"""

        filenames, kwargs, filenames2 = copy.deepcopy(data)
        kwargs["columns_lambda1"] = [1, 4]
        with pytest.raises(
            ValueError,
            match=r"Lambda value found in a file does not align with those in the filenames. Check that 'columns_lambda1\[1\]'",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_prec_2(self, data):
        """Test error no file"""

        filenames, kwargs, filenames2 = copy.deepcopy(data)
        kwargs["columns_lambda1"] = [4, 1]
        with pytest.raises(
            ValueError,
            match=r"Lambda value found in a file does not align with those in the filenames. Check that 'columns_lambda1\[0\]'",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_duplicate_files(self, data):
        """Test error when two files for the same data is present."""

        filenames, kwargs, _ = copy.deepcopy(data)
        filenames.append(filenames[2])
        with pytest.raises(
            ValueError,
            match=r"Energy values already available for lambda,",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)

    def test_u_nk_error_dU(self, data):
        """Test error when two files for the same data is present."""

        filenames, kwargs, _ = copy.deepcopy(data)
        kwargs["column_dU"] = 1
        with pytest.raises(
            ValueError,
            match=r"The difference in dU should be zero when lambda = lambda'",
        ):
            u_nk = lmp.extract_u_nk(filenames, 300, **kwargs)


class TestLammpsTI:

    @staticmethod
    @pytest.fixture(scope="class")
    def data():
        dataset = load_benzene()
        leg = "2_vdw"
        filenames = dataset["data"]["ti"][leg]
        kwargs = kwargs_ti[leg]
        return filenames, kwargs

    def test_dHdl_error_col_lam1(self, data):
        """Test error when two files for the same data is present."""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_lambda1"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column_lambda1 must be type 'int', instead of <class 'str'>",
        ):
            dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)

    def test_dHdl_error_col_lam2(self, data):
        """Test error when two files for the same data is present."""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_lambda2"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column_lambda2 must be type 'int', instead of <class 'str'>",
        ):
            dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)

    def test_dHdl_error_col_dlam1(self, data):
        """Test error when two files for the same data is present."""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_dlambda1"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column_dlambda1 must be type 'int', instead of <class 'str'>",
        ):
            dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)

    def test_dHdl_error_col_dU(self, data):
        """Test error when two files for the same data is present."""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["columns_derivative"] = [1.1]
        with pytest.raises(
            ValueError,
            match=r"Provided columns for derivative values must have a length of two,",
        ):
            dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)

        kwargs["columns_derivative"] = [1.1, 1]
        with pytest.raises(
            ValueError,
            match=r"Provided column for columns_derivative must be type int. columns_derivative:",
        ):
            dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)

    def test_lam2(self, data):
        """Test two lambda values"""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_lambda2"] = 3

        dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)
        assert dHdl.index.names == ["time", "coul-lambda", "vdw-lambda"]

        kwargs["vdw_lambda"] = 2
        dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)
        assert dHdl.index.names == ["time", "coul-lambda", "vdw-lambda"]

    def test_dHdl_error_no_file(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames.append("test_test_1_1_test_1.txt")

        with pytest.raises(
            ValueError,
            match=r"File not found: test_test_1_1_test_1.txt",
        ):
            dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)

    def test_dHdl_error_num_cols(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames2 = load_benzene()["data"]["ti"]["1_coul-off"]
        ind1 = [i for i, x in enumerate(filenames) if "_1" in x][0]
        ind2 = [i for i, x in enumerate(filenames2) if "_1" in x][0]
        filenames[ind1] = filenames2[ind2]
        filenames.append("test_test_1_1_test_1.txt")

        with pytest.raises(
            ValueError,
            match=r"Number of columns, 9, is less than index: \[0, 1, 2, 9, 8\]",
        ):
            dHdl = lmp.extract_dHdl(filenames, 300, **kwargs)


class TestLammpsH:

    @staticmethod
    @pytest.fixture(scope="class")
    def data():
        dataset = load_benzene()
        leg = "2_vdw"
        filenames = dataset["data"]["ti"][leg]
        kwargs = {
            "column_lambda1": 1,
            "column_pe": 5,
            "ensemble": "npt",
            "pressure": pressure,
        }
        return filenames, kwargs

    def test_H_error_no_glob(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames = "test_test_1_1_test_1.txt"

        with pytest.raises(
            ValueError,
            match=r"No files have been found that match: test_test_1_1_test_1.txt",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

    def test_H_error_no_file(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames.append("test_test_1_1_test_1.txt")

        with pytest.raises(
            ValueError,
            match=r"File not found: test_test_1_1_test_1.txt",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

    def test_H_npt_nvt(self, data):
        """Test ensembles"""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)

        H = lmp.extract_H(filenames, 300, **kwargs)
        assert H.index.names == ["time", "fep-lambda"]

        kwargs["ensemble"] = "nvt"
        del kwargs["pressure"]
        H = lmp.extract_H(filenames, 300, **kwargs)
        assert H.index.names == ["time", "fep-lambda"]

        kwargs["ensemble"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Only ensembles of nvt or npt are supported.",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

    def test_H_error_npt_nvt_pressure(
        self,
        data,
    ):
        """Test ensembles with incorrect pressure"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)

        kwargs["ensemble"] = "nvt"
        with pytest.raises(
            ValueError,
            match=r"There is no volume correction in the nvt ensemble, the pressure value will not be used.",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

        kwargs["ensemble"] = "npt"
        del kwargs["pressure"]
        with pytest.raises(
            ValueError,
            match=r"In the npt ensemble, a pressure must be provided in the form of a positive float",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

    def test_H_error_col_lam1(self, data):
        """Test type col lambda 1"""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_lambda1"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column_lambda1 must be type 'int', instead of",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

    def test_u_nk_error_col_lam2(self, data):
        """Test error type col lambda 2"""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_lambda2"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column_lambda2 must be type 'int', instead of <class 'str'>",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

    def test_H_error_col_pe(self, data):
        """Test error col pe"""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_pe"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column_pe must be type 'int', instead of <class 'str'>",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)

    def test_H_error_num_cols(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_volume"] = 10

        with pytest.raises(
            ValueError,
            match=r"Number of columns, 10, is less than index: \[0, 1, 5, 10\]",
        ):
            H = lmp.extract_H(filenames, 300, **kwargs)


class TestLammpsLJDimer_TI:

    @staticmethod
    @pytest.fixture(scope="class")
    def data():
        dataset = load_lj_dimer()
        filenames = dataset["data"]
        kwargs = {"column_lambda": 1, "column_u_cross": 10, "units": "lj", "prec": 1}
        return filenames, kwargs

    def test_H_error_no_glob(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames = "test_test_1_1_test_1.txt"

        with pytest.raises(
            ValueError,
            match=r"No files have been found that match: test_test_1_1_test_1.txt",
        ):
            H = lmp.extract_dHdl_from_u_n(filenames, T_lj, **kwargs)

    def test_H_error_no_file(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames = copy.deepcopy(filenames)
        filenames.append("test_test_1_1_test_1.txt")

        with pytest.raises(
            ValueError,
            match=r"File not found: test_test_1_1_test_1.txt",
        ):
            H = lmp.extract_dHdl_from_u_n(filenames, T_lj, **kwargs)

    def test_H_error_col_lam1(self, data):
        """Test type col lambda 1"""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_lambda"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for lambda must be type int. column_lambda:",
        ):
            H = lmp.extract_dHdl_from_u_n(filenames, T_lj, **kwargs)

    def test_H_error_col_u_cross(self, data):
        """Test error col u_cross"""

        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_u_cross"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for u_cross must be type int. column_u_cross:",
        ):
            H = lmp.extract_dHdl_from_u_n(filenames, T_lj, **kwargs)

    def test_H_error_num_cols(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_u_cross"] = 12

        with pytest.raises(
            ValueError,
            match=r"Number of columns, 11, is less than index: \[0, 1, 12\]",
        ):
            H = lmp.extract_dHdl_from_u_n(filenames, T_lj, **kwargs)


class TestLammpsLJDimer_MBAR:

    @staticmethod
    @pytest.fixture(scope="class")
    def data():
        dataset = load_lj_dimer()
        filenames = dataset["data"]
        kwargs = {
            "column_lambda": 1,
            "column_U_cross": 10,
            "units": "lj",
            "prec": 1,
            "pressure": P_lj,
            "ensemble": "npt",
            "column_U": 5,
        }
        return filenames, kwargs

    def test_u_nk_npt_error(
        self,
        data,
    ):
        """Test that initializing u_nk from NPT fails without pressure"""
        filenames, kwargs = copy.deepcopy(data)
        del kwargs["pressure"]

        with pytest.raises(
            ValueError,
            match=r"In the npt ensemble, a pressure must be provided in the form of a positive float",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_unknown_ensemble(
        self,
        data,
    ):
        """Test that initializing u_nk that only known ensembles are accepted"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs["ensemble"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Only ensembles of nvt or npt are supported.",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_nvt_with_pressure(
        self,
        data,
    ):
        """Test that initializing u_nk that only known ensembles are accepted"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs["ensemble"] = "nvt"
        with pytest.raises(
            ValueError,
            match=r"There is no volume correction in the nvt ensemble, the pressure value will not be used.",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_error_no_file(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames = copy.deepcopy(filenames)
        filenames.append("test_test_1_1_test_1.txt")

        with pytest.raises(
            ValueError,
            match=r"File not found: test_test_1_1_test_1.txt",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_error_no_path(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        filenames = "test_test_1_1_test_1.txt"

        with pytest.raises(
            ValueError,
            match=r"No files have been found that match: test_test_1_1_test_1.txt",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_col_type_error(
        self,
        data,
    ):
        """Test columns_lambda type error"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs["column_lambda"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for lambda must be type int. column_u_lambda:",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_col_Ucross_type_error(
        self,
        data,
    ):
        """Test column_U_cross type error"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs["column_U_cross"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for `U_cross` must be type int. column_U_cross:",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_col_U_type_error(
        self,
        data,
    ):
        """Test column_dU type error"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs["column_dU"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for `U` must be type int. column_U:",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_col_U_type_error(
        self,
        data,
    ):
        """Test column_U type error"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs["column_U"] = "test"
        with pytest.raises(
            ValueError,
            match=r"Provided column for `U` must be type int. column_U: test, type: <class 'str'>",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_error_duplicate_files(self, data):
        """Test error when two files for the same data is present."""

        filenames, kwargs = copy.deepcopy(data)
        filenames.append(filenames[2])
        with pytest.raises(
            ValueError,
            match=r"Energy values already available for lambda,",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)

    def test_u_nk_error_num_cols(
        self,
        data,
    ):
        """Test error no file"""
        filenames, kwargs = copy.deepcopy(data)
        kwargs = copy.deepcopy(kwargs)
        kwargs["column_U_cross"] = 12

        with pytest.raises(
            ValueError,
            match=r"Number of columns, 11, is less than indices: \[12\]",
        ):
            u_nk = lmp.extract_u_nk_from_u_n(filenames, T_lj, **kwargs)
