import numpy as np 
import matplotlib.pyplot as plt
import pandas as pd
import skrf as rf
import time

class material:
    """"
    material class defines BAW materials, such as Ru, AlScN, SiO2, etc.
    """
    def __init__(self, name, rho, c33, e33, eps33):
        self.name = name
        self.rho = rho                          # density, kg/m^3
        self.c33 = c33                          # stiffness, Pa
        self.e33 = e33                          # coupling, C/m^2
        self.eps33 = eps33                      # ABSOLUTE permittivity F/m

    def velocity(self):
        if self.eps33 == 0:
            K2 = 0
        else: 
            K2 = self.e33**2 / self. c33 / self.eps33
        c33D = self.c33 * (1+K2)
        return np.sqrt(c33D / self.rho)  # acoustic velocity
    
    def impedance(self):
        if self.eps33 == 0:
            K2 = 0
        else: 
            K2 = self.e33**2 / self. c33 / self.eps33
        c33D = self.c33 * (1+K2)
        return np.sqrt(c33D * self.rho)  # acoustic impedance per unit Area
    
def Z_matrix_elastic(mat, d, A, w):
    """
    calculates the frequency dependent non-piezo elastic material impedance matrix. It is 2-port network
    """
    k = w / mat.velocity()
    ZT = mat.impedance() * A

    z11 = ZT / (1j * np.tan(k*d))
    z12 = ZT / (1j * np.sin(k*d))
    z21 = z12
    z22 = z11

    Z = np.zeros((2, 2, len(w)), dtype=np.complex128)
    Z[0,0,:] = z11
    Z[0,1,:] = z12
    Z[1,0,:] = z21
    Z[1,1,:] = z22

    return Z


def Z_matrix_piezo(mat, d, A, w):
    """
    calculates the frequency dependent piezo elastic material impedance matrix. It is 3-port network
    """
    k = w / mat.velocity()
    ZT = mat.impedance() * A
    h = mat.e33 / mat.eps33
    C0 = mat.eps33 * A / d

    z11 = ZT / (1j * np.tan(k*d))
    z12 = ZT / (1j * np.sin(k*d))
    z13 = h / (1j * w)
    z21 = z12
    z22 = z11
    z23 = z13
    z31 = z13
    z32 = z23
    z33 = 1 / (1j * w * C0)

    Z = np.zeros((3, 3, len(w)), dtype=np.complex128)
    Z[0,0,:] = z11
    Z[0,1,:] = z12
    Z[0,2,:] = z13
    Z[1,0,:] = z21
    Z[1,1,:] = z22
    Z[1,2,:] = z23
    Z[2,0,:] = z31
    Z[2,1,:] = z32
    Z[2,2,:] = z33

    return Z, C0


def z2abcd(Z):
    """
    convert z matrix to ABCD matrix. This conversion only suits 2-port network
    """
    detZ = Z[0,0,:] * Z[1,1,:] - Z[0,1,:] * Z[1,0,:]
    
    A = Z[0,0,:] / Z[1,0,:]
    B = detZ / Z[1,0,:]
    C = 1 / Z[1,0,:]
    D = Z[1,1,:] / Z[1,0,:]

    T = np.zeros((2, 2, Z.shape[2]), dtype=np.complex128)
    T[0,0,:] = A
    T[0,1,:] = B
    T[1,0,:] = C
    T[1,1,:] = D
    return T

def T_matrix_elastic(mat, d, A, w):
    """
    Calculate frequency dependent ABCD matrix from material parameters. It is only suitable for non-piezo material and thus, it is 
    2-port network. Cascade ABCD matrix layer by layer to simulate BAW stack.
    """
    Z = Z_matrix_elastic(mat, d, A, w)
    T = z2abcd(Z)
    return T

def Adaptive_Mason(stack_info, A, w):
    """
    Mason main function. Seperate BAW stack into 3 parts: bottom 2-port, top 2-port, and PZL 3-port. Calculate the T matrix of these 3 parts seperately and then, assemble them togother to get the 3-port impedance matrix
    """
    ######################### Transmission line of bottom (2-port) ####################################
    terminal_1 = np.where(stack_info.Terminal == 1)[0][0]
    for idx in range(terminal_1, stack_info.shape[0]):
        mat = material(name=stack_info.Material[idx], rho=stack_info.rho[idx], c33=stack_info.c33[idx], e33=0, eps33=0)
        thk = stack_info.THK[idx] * 1e-9
        if idx == terminal_1:
            Tb = T_matrix_elastic(mat, thk, A, w)
        else:
            T_mid = T_matrix_elastic(mat, thk, A, w)
            c11 = Tb[0,0,:] * T_mid[0,0,:] + Tb[0,1,:] * T_mid[1,0,:]
            c12 = Tb[0,0,:] * T_mid[0,1,:] + Tb[0,1,:] * T_mid[1,1,:]
            c21 = Tb[1,0,:] * T_mid[0,0,:] + Tb[1,1,:] * T_mid[1,0,:]
            c22 = Tb[1,0,:] * T_mid[0,1,:] + Tb[1,1,:] * T_mid[1,1,:]
            Tb[0,0,:] = c11
            Tb[0,1,:] = c12
            Tb[1,0,:] = c21
            Tb[1,1,:] = c22
    #######################################################################################################
    ############################### Transmission line of top (2-port) #####################################
    terminal_2 = np.where(stack_info.Terminal == 2)[0][0]
    for idx in range(terminal_2, -1, -1):
        mat = material(name=stack_info.Material[idx], rho=stack_info.rho[idx], c33=stack_info.c33[idx], e33=0, eps33=0)
        thk = stack_info.THK[idx] * 1e-9
        if idx == terminal_2:
            Tt = T_matrix_elastic(mat, thk, A, w)
        else:
            T_mid = T_matrix_elastic(mat, thk, A, w)
            c11 = Tt[0,0,:] * T_mid[0,0,:] + Tt[0,1,:] * T_mid[1,0,:]
            c12 = Tt[0,0,:] * T_mid[0,1,:] + Tt[0,1,:] * T_mid[1,1,:]
            c21 = Tt[1,0,:] * T_mid[0,0,:] + Tt[1,1,:] * T_mid[1,0,:]
            c22 = Tt[1,0,:] * T_mid[0,1,:] + Tt[1,1,:] * T_mid[1,1,:]
            Tt[0,0,:] = c11
            Tt[0,1,:] = c12
            Tt[1,0,:] = c21
            Tt[1,1,:] = c22

    #######################################################################################################
    ############################### Transmission line of PZL (3-port) #####################################
    for idx in range(terminal_1-1, terminal_2, -1):
        mat = material(name=stack_info.Material[idx], rho=stack_info.rho[idx], c33=stack_info.c33[idx], e33=stack_info.e33[idx], eps33=stack_info.eps33[idx])
        thk = stack_info.THK[idx] * 1e-9

        if idx == terminal_1-1:
            [Zp, C0] = Z_matrix_piezo(mat, thk, A, w)
            C0 = np.real(C0)
        else:
            [Zp2, C02] = Z_matrix_piezo(mat, thk, A, w)
            C0 = 1 / (1/C0 + 1/np.real(C02))

            Zp12 = np.zeros((3, 3, len(w)), dtype=np.complex128)
            Zp12[0,0,:] = Zp[0,0,:] + (Zp[0,1,:] * Zp[1,0,:]) / (-Zp[1,1,:]-Zp2[0,0,:])
            Zp12[0,1,:] = (-Zp[0,1,:] * Zp2[0,1,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp12[0,2,:] = Zp[0,2,:] - Zp[0,1,:] * (Zp2[0,2,:] - Zp[1,2,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp12[1,0,:] = (-Zp2[1,0,:] * Zp[1,0,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp12[1,1,:] = Zp2[1,1,:] + (Zp2[1,0,:] * Zp2[0,1,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp12[1,2,:] = Zp2[1,2,:] + Zp2[1,0,:] * (Zp2[0,2,:] - Zp[1,2,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp12[2,0,:] = Zp[2,0,:] - Zp[1,0,:] * (Zp2[2,0,:] - Zp[2,1,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp12[2,1,:] = Zp2[2,1,:] + Zp2[0,1,:] * (Zp2[2,0,:] - Zp[2,1,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp12[2,2,:] = Zp[2,2,:] + Zp2[2,2,:] + (Zp2[2,0,:] - Zp[2,1,:]) * (Zp2[0,2,:] - Zp[1,2,:]) / (-Zp[1,1,:] - Zp2[0,0,:])
            Zp = Zp12
    ##########################################################################################################
    ####################################### Assemble Final Impedance Matrix ##################################
    X = np.zeros((3, 3, len(w)), dtype=np.complex128)
    X[0,0,:] = -Zp[0,0,:] * Tb[1,1,:] - Tb[0,1,:]
    X[0,1,:] = -Zp[0,1,:] * Tt[1,1,:]
    X[0,2,:] = Zp[0,2,:]

    X[1,0,:] = -Zp[1,0,:] * Tb[1,1,:]
    X[1,1,:] = -Zp[1,1,:] * Tt[1,1,:] - Tt[0,1:]
    X[1,2,:] = Zp[1,2,:]

    X[2,0,:] = -Zp[2,0,:] * Tb[1,1,:]
    X[2,1,:] = -Zp[2,1,:] * Tt[1,1,:]
    X[2,2,:] = Zp[2,2,:]

    return X, C0


def Mason_FBAR(stack_info, A, w, Rs):
    """
    Calculate the impedence (Z_mason) and capacitance (C0) for FBAR. FBAR is free-free boundary condition
    Losses include dielectric loss and acoustic loss, not include resistive loss
    """
    Z, C0 = Adaptive_Mason(stack_info, A, w)
    Z_mason = np.zeros((len(w), 1), dtype=np.complex128)
    for idx in range(len(w)):
        temp = Z[1,0,idx] * Z[0,1,idx] - Z[0,0,idx] * Z[1,1,idx]
        temp2 = Z[2,0,idx] * (Z[1,1,idx]*Z[0,2,idx] - Z[0,1,idx]*Z[1,2,idx]) + Z[2,1,idx] * (Z[0,0,idx]*Z[1,2,idx] - Z[1,0,idx]*Z[0,2,idx])
        Z_mason[idx] = Z[2,2,idx] + temp2 / temp

    z11 = Z_mason + Rs
    return np.squeeze(z11), C0

def stack_info_assemble(df_Stack, df_MPara):
    """
    Join stack table and material parameter table, output a new table with stack thickness, material, and loss
    """
    Layer_Name = []
    Terminal = []
    THK = []
    Material = []
    rho = []
    c33 = []
    e33 = []
    eps33 = []

    for idx in range(df_Stack.shape[0]):
        Layer_Name.append(df_Stack['Layer_Name'].iloc[idx])
        Terminal.append(df_Stack['Terminal'].iloc[idx])
        THK.append(df_Stack['THK_nm'].iloc[idx])
        Material.append(df_Stack['Material'].iloc[idx])

        if df_Stack['Q_Mech'].iloc[idx] == -99:
            Q_Mech = np.inf
        else:
            Q_Mech = df_Stack['Q_Mech'].iloc[idx]

        if df_Stack['Q_Die'].iloc[idx] == -99:
            Q_Die = np.inf
        else:
            Q_Die = df_Stack['Q_Die'].iloc[idx]

        rho_header = Material[idx] + '_rho'
        c33_header = Material[idx] + '_c33'
        e33_header = Material[idx] + '_e33'
        eps33_header = Material[idx] + '_eps33'

        rho.append(df_MPara[rho_header].iloc[0])
        c33.append(df_MPara[c33_header].iloc[0] * (1+1j/Q_Mech))

        try:
            eps33.append(df_MPara[eps33_header].iloc[0] * (1-1j/Q_Die))
        except:
            eps33.append(0)

        try:
            e33.append(df_MPara[e33_header].iloc[0])
        except:
            e33.append(0)

    stack_info = pd.DataFrame({'Layer_Name': Layer_Name, 'Terminal': Terminal, 'THK': THK, 'Material': Material, 'rho': rho, 'c33': c33, 'eps33': eps33, 'e33': e33})

    stack_info = stack_info.drop(stack_info[stack_info.THK==0].index)
        
    return stack_info.reset_index(drop=True)


if __name__ == '__main__':

    df_Stack = pd.read_csv('Stack1.csv')
    df_MPara = pd.read_csv('Material1.csv')
    stack_info = stack_info_assemble(df_Stack, df_MPara)

    Area = 10000/1e12
    f = np.arange(1e9, 3e9, 0.1e6)
    Rs = 0.0

    start = time.perf_counter()
    z11, C0 = Mason_FBAR(stack_info, Area, 2*np.pi*f, Rs)
    end = time.perf_counter()
    print(f"time consuming: {end-start: .4f}sec")

    net = rf.Network(frequency=f, z=z11, f_unit='Hz')

    plt.figure(1)
    plt.plot(net.f, net.y_db[:,0,0])
    plt.show()

