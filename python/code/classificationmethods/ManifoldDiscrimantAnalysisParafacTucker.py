from abc import ABC, abstractmethod
import numpy as np
from scipy.stats import ortho_group  
import pymanopt as pymanopt
import tensorflow as tf
from tensorflow import keras

class ManifoldDiscrimantAnalysis(ABC):
    def __init__(self, Xs, classes, lowerdims=None, Us=None, opts=None, usestoppingcrit=True, maxits=1000, store={'Rw': 0, 'Rb': 0, 'QtRb': 0, 'QtRw':  0, 'QtBQ': 0, 'QtWQ': 0, 'QtWQinvQtBQ': 0, 'FdwrtQ': 0}, optmeth='ManOpt'):
        self.Xs=Xs
        self.classes=classes
        self.lowerdims=lowerdims
        self.Us=Us
        self.opts=opts
        self.usestoppingcrit=usestoppingcrit
        self.maxits=maxits
        self.store=store
        self.optmeth=optmeth
        if lowerdims==None:
            self.lowerdims=np.size(Xs[0])
        if optmeth not in ['bo13', 'wen12', 'ManOpt']:
            self.optmeth='ManOpt'
            print("Chosen optimization method", optmeth, "has not been implemented")
        self.Fdifftol=Fdifftol=10**(-10)
        self.Udifftol=Udifftol=10**(-12)
        self.Xsample1 = Xs[0];

        self.sizeX = np.shape(self.Xsample1);

        self.nmodes = len(self.sizeX);

        self.nsamples = np.shape(Xs);
        self.F=0
        self.G={'U1': 0, 'U2': 0}
        if Us==None:
            for i in range(self.nmodes):
                Us[i]=ortho_group.rvs(dim=(np.shape(self.sizeX)[i])) #Contemplate changing this

        
    def SetTolerances(self,Fdifftol=10**(-10), Udifftol=10**(-12)):
        self.Fdifftol=Fdifftol
        self.Udifftol=Udifftol
        
    @abstractmethod 
    def ObjectMatrixData(self, U,x, store, classmeandiffs, observationdiffs, nis, K1, K2,): #This is a virtual function that any inheriting subclass should realize
        return(None)
        
    @abstractmethod
    def QtCalculator(self):
        return(None)
    def QtCheck(self):
        return(None)
        
    def MyCost(self, x, store, classmeandiffs, observationdiffs, nis, K1, K2, Rw, Rb):
        self.ObjectMatrixData(self,x, store, classmeandiffs, observationdiffs, nis, K1, K2)
        self.F=-np.linalg.trace(self.store['QtWQinvQtBQ'])
        
    def MyGrad(self):

            """
            Matlab code implementing the calculation of the gradient: 
                Why can't we do this in TensorFlow or with autograd?
            TTT=reshape(permute(reshape(FdwrtQ, M, N, 1, K), [2 4 1 3]),[N*K M]);
            TTT3d = permute(reshape(TTT', [M, N, K]), [2 1 3]);
            G1 = cell2mat(arrayfun(@(x)(TTT3d(:,:,x)*U2(:,x)), 1:K, 'UniformOutput', false));
                           


            TTT=reshape(permute(reshape(FdwrtQ, M, N, K, 1), [2 4 1 3]),[N M*K]);
            TTT3d = permute(reshape(TTT, [N, M, K]), [2 1 3]);
            G2 = cell2mat(arrayfun(@(x)(TTT3d(:,:,x)*U1(:,x)), 1:K, 'UniformOutput', false));

            """
            
            self.G['U1'] = -G1;
            self.G['U2'] = -G2;
    def ClassBasedDifferences(self):
         """
         We should implement the classbased_differences method from the MATLAB code here. 
         """
    def CalculateYs(self):
        """
        Calculate Y
        """
    def OptimizeOnManifold(self):
        
class TuckerDiscriminantAnalysis(ManifoldDiscrimantAnalysis):
    def QtCheck(self,Qt):
        if self.store[Qt]==0:
            self.store[Qt]=self.QtCalculator(Qt)
    def QtCalculator(self,Qt,N=None,K1=None,K2=None,U1=None,U2=None):
            if Qt in {'QtRw', 'QtRb'}:
                Qt_mm=np.tensordot(np.tensordot(self.Qt[:-2],np.linalg.transpose(U1),axes=(1,0)),np.linalg.transpose(U2),axes=(2,0)) #Something might be horribly wrong here...
                Qt_temp=np.reshape(np.rollaxis(Qt_mm,(1,0,2))(K2*K1,N)) #Not sure if this is the correct approach. Need MATLAB license to test original behavior
            if Qt in {'QtWQ', 'QtBQ'}:
                Qt_temp=np.dot(self.store['QtRw'],self.store['QtRw']))
            if Qt in {'QtWQinvQtBQ'}:
                Qt_temp=np.dot(self.store['QtWQ'],np.linalg.inv(self.store['QtBQ'])))          
            else: 
                print("Wrong Qt specified")
            self.store[Qt]=Qt_temp
            
    def ObjectMatrixData(self, U, x, store, classmeandiffs, observationdiffs, nis, K1, K2,):
        if (self.store['Rw']==[] or self.store['Rb']==[]):
            obsExample=classmeandiffs[0]
            sizeObs=np.shape(obsExample)
            I=sizeObs[0]
            J=sizeObs[1]
            if self.store['Rw']==0: #What if only one of them is missing? Shouldn't we still calculate the missing one? Split the code below into two parts, one for each case. This has been done now, but not in the MATLAB code
                nclasses=max(np.shape(classmeandiffs)) #This is a straight-copy of the existing MATLAB code, not sure if this is the intended behavior there either...
                classmeandiffstensor=np.reshape(classmeandiffs,(I,J,nclasses),order="F")
                Rb=classmeandiffstensor
            if self.store['Rb']==0:
                nobs=max(np.shape(observationdiffs))
                observationdiffstensor=np.reshape(observationdiffs,(I,J,nobs),order="F")
                Rw=observationdiffstensor
            self.store['Rw'] = Rw
            self.store['Rb'] = Rb
#        Rw=store['Rw'] #This assignment SHOULD be superflous now...
#        Rw=store['Rb']
        Rwsize = np.shape(Rw)
        nobs=Rwsize[-1]
        datadims=np.shape(Rb)
        nclasses=len(datadims)
        N=datadims[0] #This is a point where the two-dimensionality is hardcoded..
        M=datadims[1]
        #We proceed to calculate all relevant matrices for the optimization step. 
        for j in {'QtRw', 'QtRb', 'QtWQ', 'QtBQ', 'QtWQinvQtBQ', 'FdwrtQ'}:
            self.QtCheck(j)
        
        
class PARAFACDiscriminantAnalysis(ManifoldDiscrimantAnalysis):    
    def ObjectMatrixData(U, cmean_m_xmeans, xi_m_cmeans, nis, K1, K2):
        
        
        return()