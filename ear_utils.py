from scipy.spatial import distance as dist

def calcular_ear(olho):
    """
    Calcula o Eye Aspect Ratio (EAR) para um olho
    """
    # Calcula as distâncias verticais
    A = dist.euclidean(olho[1], olho[5])
    B = dist.euclidean(olho[2], olho[4])
    
    # Calcula a distância horizontal
    C = dist.euclidean(olho[0], olho[3])
    
    # Calcula o EAR
    ear = (A + B) / (2.0 * C)
    return ear
