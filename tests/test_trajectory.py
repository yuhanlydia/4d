import unittest
from opt4d.trajectory import TrajectoryFit, project_trajectory_to_linear, homotopy_scenes

SCENE={"schema_version":1,"video":{"width":160,"height":90,"frames":9,"fps":8.0},
"camera":{"intrinsics":[[160,0,80],[0,160,45],[0,0,1]],"extrinsic":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]},
"objects":[{"id":1,"name":"o","kind":"cube","size":[1,1,1],"position":[0,0,4],"rotation_euler":[0,0,0],"motion":{"type":"static"}}]}

class TrajectoryTests(unittest.TestCase):
 def test_projection_zero_weight_preserves_static_velocity(self):
  fit=TrajectoryFit([0,1],[[0,0],[10,0]],0,0); s=project_trajectory_to_linear(SCENE,fit,physics_weight=0)
  self.assertEqual(s["objects"][0]["motion"]["velocity"],[0.0,0.0,0.0])
 def test_homotopy_schedule(self):
  fit=TrajectoryFit([0,1],[[0,0],[10,0]],0,0); hs=homotopy_scenes(SCENE,fit)
  self.assertEqual([w for w,_ in hs],[0,.25,.5,.75,1])
  self.assertGreater(hs[-1][1]["objects"][0]["motion"]["velocity"][0],0)
if __name__=="__main__":unittest.main()
