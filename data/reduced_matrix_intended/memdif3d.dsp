# memdif3d input written by xlsx2memdif.py from Reduced_Matrix.xlsx
# Mass-transfer coefficient K = D * porosity / length / tortuosity
BEGIN sand
  DIFFUSION 0.125
  TORTUOSITY 2.5
  POROSITY 0.3
  LENGTH 1.0
END sand

BEGIN membrane
  DIFFUSION 0.125
  TORTUOSITY 1.0
  POROSITY 0.02
  LENGTH 0.3
END membrane
