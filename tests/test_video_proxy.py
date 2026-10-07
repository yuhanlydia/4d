import unittest
import numpy as np
from opt4d.video_proxy import PROXY_MODES, PROXY_WEIGHTS, proxy_components

class VideoProxyTests(unittest.TestCase):
    def test_modes_are_nested_ablation(self):
        self.assertEqual(PROXY_MODES, ("flow","flow_mask","flow_mask_track"))
        self.assertEqual(PROXY_WEIGHTS["flow"]["mask"],0.0)
        self.assertEqual(PROXY_WEIGHTS["flow_mask"]["track"],0.0)
        self.assertEqual(PROXY_WEIGHTS["flow_mask_track"]["track"],1.0)

    def test_components_zero_for_identical_measurements(self):
        m={"flow":[np.array([[1.,0.]])],"mask":[0.2],"track":[np.array([[1.,0.]])]}
        c=proxy_components(m,m)
        for value in c.values(): self.assertAlmostEqual(value,0.0,places=9)

if __name__=="__main__": unittest.main()
